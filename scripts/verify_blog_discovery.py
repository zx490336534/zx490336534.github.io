# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4==4.15.0", "lxml==6.1.3"]
# ///
"""Verify the generated discovery contract and optionally compare protected content."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from blog_discovery import EVIDENCE, WATCH, caption_cues, watch_path
from blog_geo import HARD_RISK, SENSITIVE_LINE, compact, fragments, safe
from blog_portfolio import dimensions

SITE = "https://www.zhongxin.website"
ROOT = Path(__file__).resolve().parents[1]
NS = {"map": "http://www.sitemaps.org/schemas/sitemap/0.9", "video": "http://www.google.com/schemas/sitemap-video/1.1"}


def target(path):
    f = ROOT / unquote(path).lstrip("/")
    return f / "index.html" if path.endswith("/") else f


def page(p):
    return BeautifulSoup(target(p).read_text(), "lxml")


def old_page(commit, p):
    rel = target(p).relative_to(ROOT)
    raw = subprocess.check_output(["git", "show", f"{commit}:{rel}"], cwd=ROOT)
    return BeautifulSoup(raw, "lxml")


def verify_calendar_archive(calendar):
    for year, months in calendar.items():
        year_url = f"/archives/{year}/"
        year_page = page(year_url)
        links = year_page.select('nav[aria-label="按月份浏览"] a')
        expected_links = [(f"{year_url}{month}/", f"{len(months[month])} 篇") for month in sorted(months, reverse=True)]
        assert [(link["href"], link.small.get_text(strip=True)) for link in links] == expected_links, year_url
        year_articles = []
        for month in sorted(months, reverse=True):
            month_url = f"{year_url}{month}/"
            month_page = page(month_url)
            expected = [path for _, path in sorted(months[month], reverse=True)]
            assert [a["href"] for a in month_page.select(".post-list .row-title")] == expected, month_url
            assert month_page.select_one(f'main a[href="{year_url}"]'), month_url
            year_articles.extend(expected)
        assert [a["href"] for a in year_page.select(".post-list .row-title")] == year_articles, year_url


def verify_legacy_tag_pages():
    for file in (ROOT / "tags").glob("*/page/*/index.html"):
        parent = file.parents[2]
        index = BeautifulSoup((parent / "index.html").read_text(), "lxml")
        archived = BeautifulSoup(file.read_text(), "lxml")
        back = archived.select_one("main .listing > p a")
        assert back and target(back["href"]) == parent / "index.html", file
        tag = index.h1.get_text(strip=True)
        count = len(index.select(".post-list .row-title"))
        assert back.get_text(strip=True) == f"查看「{tag}」标签当前收录的 {count} 篇文章", file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", help="Git revision used to verify article body and video preservation")
    args = parser.parse_args()
    sitemap = ET.parse(ROOT / "sitemap.xml")
    paths = [urlsplit(loc.text).path for loc in sitemap.findall("map:url/map:loc", NS)]
    assert len(paths) == len(set(paths)) and not any(path.startswith("/teaching-") for path in paths)
    assert all(loc.text == SITE + p for loc, p in zip(sitemap.findall("map:url/map:loc", NS), paths))
    robots = (ROOT / "robots.txt").read_text()
    assert f"Sitemap: {SITE}/sitemap.xml" in robots and "Disallow: /" not in robots
    articles = list((ROOT / "article").glob("*.html"))
    assert set("/article/" + article.name for article in articles) <= set(paths)
    for path in paths:
        assert target(path).is_file(), path
        markup = page(path)
        canonicals = markup.select('link[rel=canonical]')
        assert len(canonicals) == 1 and canonicals[0]["href"] == SITE + path, path

    guide_counts = Counter()
    calendar = defaultdict(lambda: defaultdict(list))
    for article in articles:
        path = "/article/" + article.name
        markup = page(path)
        published = markup.select_one('time[itemprop~="datePublished"]')["datetime"]
        calendar[published[:4]][published[5:7]].append((published, path))
        data = json.loads(markup.select_one('script[type="application/ld+json"]').string)["@graph"]
        assert [v["@type"] for v in data] == ["BlogPosting", "BreadcrumbList"], path
        headline = markup.select_one("h1.post-title").get_text(strip=True)
        assert data[0]["headline"] == headline and data[0]["author"]["name"] == markup.select_one(".post-author").get_text(strip=True)
        assert data[0].get("articleSection") == [a.get_text(strip=True) for a in markup.select(".article-path a")][1:], path
        card = markup.select_one(".article-main > .editorial-evidence")
        assert bool(card) == (article.stem in EVIDENCE), path
        if card:
            assert len(card.select("dd")) == 3 and not markup.select_one(".post-body .editorial-evidence"), path
        guide = markup.select_one(".article-main > .reading-guide")
        assert bool(guide) != bool(card), path
        guide_counts[guide["data-reading-kind"] if guide else "original-editorial"] += 1
        original_body = markup.select_one(".post-body")
        for demo in original_body.select("video.inline-demo"):
            clip, poster = target(demo["src"]), target(demo["poster"])
            assert clip.suffix == ".mp4" and poster == clip.with_suffix(".webp"), path
            assert clip.is_file() and poster.is_file(), (path, clip, poster)
            assert demo.has_attr("controls") and demo["preload"] == "none" and not demo.has_attr("autoplay"), path
        if guide:
            assert guide.find_next_sibling() == original_body and guide.select_one("h2"), path
            assert not guide.select("script, code, pre, img, iframe"), path
            kind = guide["data-reading-kind"]
            for entry in guide.select('a[href^="#"]'):
                fragment = unquote(entry["href"][1:])
                assert fragment == "article-text" or original_body.find(id=fragment), (path, fragment)
            for entry in guide.select('nav a[href]'):
                fragment = unquote(entry["href"][1:])
                assert compact(original_body.find(id=fragment).get_text(" ", strip=True)) == entry.get_text(strip=True), path
                if kind != "editorial":
                    assert not SENSITIVE_LINE.search(fragment) and not HARD_RISK.search(fragment), path
                    assert safe(entry.get_text(strip=True), 3, 58, min_han=2), path
            if kind == "excerpt":
                quote = guide.select_one("blockquote")
                attribution = quote.select_one("cite")
                key = unquote(attribution.a["href"][1:])
                text = compact(" ".join(part for part in quote.find_all(string=True, recursive=False)))
                assert safe(text, 30, 112) and not HARD_RISK.search(text), path
                assert any(key == anchor and any(text in p for p in paragraphs)
                           for anchor, _, _, paragraphs in fragments(original_body)), path
            if kind == "restricted":
                assert not guide.select("blockquote, nav") and [a["href"] for a in guide.select("a")] == ["#article-text"], path
        track = markup.select_one(".article-video video track")
        transcripts = markup.select(".article-video > details.video-transcript")
        assert len(transcripts) == int(track is not None), path
        if track:
            assert transcripts[0].summary and not transcripts[0].has_attr("open"), path
            assert [p.get_text() for p in transcripts[0].select("p")] == [
                text for _, text in caption_cues(target(track["src"]))
            ], path
        if args.baseline:
            previous = old_page(args.baseline, path)
            assert previous.select_one(".post-body").decode_contents() == markup.select_one(".post-body").decode_contents(), path
            for panel in [*previous.select(".article-video > .video-transcript"), *transcripts]:
                panel.decompose()
            assert str(previous.select_one(".article-video")) == str(markup.select_one(".article-video")), path
            for selector in (".article-cover", "a.source-link", 'meta[property="og:image"]'):
                assert str(previous.select_one(selector)) == str(markup.select_one(selector)), (path, selector)

    for slug in WATCH:
        markup = page(watch_path(slug))
        source_url = markup.select_one("video source")["src"]
        cap = markup.select_one("video track")["src"]
        data = json.loads(markup.select_one('script[type="application/ld+json"]').string)["@graph"][0]
        assert data["@type"] == "VideoObject" and data["contentUrl"] == source_url
        sitemap_entry = next(entry for entry in sitemap.findall("map:url", NS) if entry.findtext("map:loc", namespaces=NS) == SITE + watch_path(slug))
        assert sitemap_entry.findtext("video:video/video:publication_date", namespaces=NS) == data["uploadDate"]
        assert sitemap_entry.findtext("video:video/video:content_loc", namespaces=NS) == source_url
        cues = [text for _, text in caption_cues(target(cap))]
        assert [p.get_text(strip=True) for p in markup.select(".watch-transcript section p")] == cues, slug
        art = page(f"/article/{slug}.html")
        assert art.select_one(".article-video video source")["src"] == source_url
        assert art.select_one(".watch-link a")["href"] == watch_path(slug)
        assert len(markup.select(".watch-transcript section")) == 5

    home = page("/")
    assert len(home.select("h1")) == 1 and all(word in home.title.string for word in ("测试游记", "AI Agent", "自动化"))
    assert home.select_one('.publication-intro a[href="/series/agent-development/"]')
    assert home.select_one('.publication-intro a[href="/about/"]')
    assert len(page("/series/agent-development/").select("#case-reads ~ ul li")) == 5
    tool = page("/tools/test-cases/")
    assert tool.select_one(".tool-guide h1") and tool.select_one("#root") and tool.select_one("#site-analytics")
    assert len(tool.select('meta[name="description"]')) == 1
    if args.baseline:
        before = old_page(args.baseline, "/tools/test-cases/")
        assert [s.string for s in before.select("script:not([src])")] == [s.string for s in tool.select("script:not([src])")]
    must_email = "mailto:490336534@qq.com"
    for address in ("/", "/archives/", "/series/agent-development/", "/videos/", "/article/promptfoo-agent-regression.html"):
        footer = page(address).select_one("footer .footer-contact")
        assert [a["href"] for a in footer.select("a[href]")] == [must_email, "https://github.com/zx490336534"], address
    assert page("/about/").select_one(f'.profile-contact a[href="{must_email}"]')
    profile = page("/about/")
    cards = profile.select("#selected-work .work-card")
    assert len(cards) == 3 and len(profile.select("h1")) == 1
    assert "AI 应用开发" in profile.select_one(".page-heading p").get_text(strip=True)
    assert profile.select_one(f'.work-profile-links a[href="{must_email}"]')
    assert [a["href"] for a in home.select(".home-work li a")] == ["/about/#" + card["id"] for card in cards]
    for card in cards:
        assert [dt.get_text(strip=True) for dt in card.select("dt")] == ["怎么做", "怎么核对"]
        for a in card.select('a[href^="/"]'):
            link = urlsplit(a["href"])
            assert target(link.path).is_file() and (not link.fragment or page(link.path).find(id=link.fragment)), a["href"]
    assert profile.select_one('.work-card a[href="https://github.com/zx490336534/next-ai-test-cases"]')
    from blog_portfolio import CODEX_EVIDENCE_TEST, CODEX_RELEASE
    plugin_card = profile.select_one("#ai-test-cases")
    assert plugin_card.select_one(f'a[href="{CODEX_RELEASE}"]')
    assert plugin_card.select_one(f'a[href="{CODEX_EVIDENCE_TEST}"]')
    assert "仍可查到当时执行的版本" in plugin_card.get_text(" ", strip=True)
    assert must_email not in profile.select_one('script[type="application/ld+json"]').string
    if args.baseline:
        assert old_page(args.baseline, "/about/").select_one(".post-body").decode_contents() == profile.select_one(".post-body").decode_contents()
    from blog_portfolio import PROFILE_SHARE_ALT, PROFILE_SHARE_IMAGE
    assert profile.select_one('head meta[property="og:type"]')["content"] == "website"
    if target(PROFILE_SHARE_IMAGE).is_file():
        expected_share = {"og:image": SITE + PROFILE_SHARE_IMAGE, "og:image:type": "image/jpeg",
                          "og:image:width": "1586", "og:image:height": "992",
                          "og:image:alt": PROFILE_SHARE_ALT}
        for key, value in expected_share.items():
            matches = profile.select(f'head meta[property="{key}"]')
            assert len(matches) == 1 and matches[0]["content"] == value, key
    demo_prefix = "/videos/portfolio/ai-test-cases-demo-v5"
    demo_files = [demo_prefix + suffix for suffix in (".mp4", ".webp", ".zh-CN.vtt")]
    demo_exists = all(target(path).is_file() and target(path).stat().st_size for path in demo_files)
    demo = profile.select_one("#ai-test-cases figure.work-demo")
    assert bool(demo) == demo_exists
    if demo:
        assert demo.select_one("figcaption").get_text(strip=True) == "完整演示｜Codex 对话与脑图：生成、增删改、执行和证据"
        media = demo.select_one("video")
        assert (media["width"], media["height"], media["preload"], media["poster"]) == ("1440", "900", "none", demo_files[1])
        assert "controls" in media.attrs and "playsinline" in media.attrs and "autoplay" not in media.attrs
        assert media.select_one("source")["src"] == demo_files[0]
        captions = media.select_one("track")
        assert captions["src"] == demo_files[2] and captions["srclang"] == "zh-CN" and "default" not in captions.attrs
        assert target(demo_files[2]).read_text().startswith("WEBVTT")
        demo_text = demo.get_text(" ", strip=True)
        for proof in ("1:09｜对话增删改", "P1 改为 P0", "2:49｜核对导出", "删除项不再出现", "3:20｜Codex 插件", "4:20｜实际执行", "4:31｜回看证据", "真实会话摘录"):
            assert proof in demo_text, proof
        assert demo.select_one("a[download]")["href"] == demo_files[0]
        sample = demo_prefix + "-sample.csv"
        assert bool(demo.select_one(f'a[download][href="{sample}"]')) == target(sample).is_file()
    assert not tool.select_one(f'a[href="{must_email}"]')
    assert "/videos/" in paths
    library = page("/videos/")
    manifest = json.loads((ROOT / "scripts/article_videos.json").read_text())
    expected = {p: v for p,v in manifest.items() if v.get("voice") == "zh-CN-XiaoxiaoNeural" and v.get("poster") and v.get("captions")}
    index = library.select(".vc-index .vc-index-play")
    assert len(index) == len(expected)
    assert library.select_one("h1").get_text(strip=True) == "视频系列"
    by_stem = {Path(path).stem: (path, video) for path, video in expected.items()}
    matched = set()
    by_card = {}
    for card in library.select(".vc-card"):
        path = card.select_one("a")["href"]
        listing = page(path)
        assert listing.select_one("link[rel=canonical]")["href"] == SITE + path
        episodes = listing.select("[data-player-episode]")
        assert episodes and len({ep["data-player-episode"] for ep in episodes}) == len(episodes)
        assert [ep["data-player-episode"] for ep in episodes if ep.has_attr("aria-current")] == [episodes[0]["data-player-episode"]]
        for ep in episodes:
            key = ep["data-player-episode"]
            original, media = by_stem[key]
            assert ep["data-article"] == original
            assert ep["data-src"] == media["src"] and ep["data-poster"] == media["poster"] and ep["data-captions"] == media["captions"]
            assert ep["href"] == (watch_path(key) if key in WATCH else original + "#article-video-title")
        first = episodes[0]
        assert listing.select_one("video source")["src"] == first["data-src"]
        assert listing.select_one("video track")["src"] == first["data-captions"]
        by_card[path] = [ep["data-player-episode"] for ep in episodes]
    for link in index:
        path, episode = link["data-player-url"].split("?episode=")
        assert episode in by_card[path] and episode not in matched
        matched.add(episode)
    assert matched == set(by_stem)
    assert set(path for path in (item for group in by_card.values() for item in group)) == matched
    for item in json.loads((ROOT / "scripts/series_catalog.json").read_text()):
        series_url = f"/series/{item['id']}/"
        series_pg = page(series_url)
        assert series_pg.select_one('.article-path a[href="/"]')
        assert series_pg.select_one(f'.article-path a[href="/series/#topic-{item["section"]}"]')
        video_link = series_pg.select_one('.series-start-links a[href^="/videos/#"]')
        order = [Path(chapter).stem for group in item["groups"] for chapter in group["chapters"] if chapter in expected]
        assert order == by_card.get(f"/videos/series/{item['id']}/", [])
        if video_link:
            assert library.find(id=video_link["href"].split("#",1)[1]), series_url
    for original, entry in expected.items():
        article_video = page(original).select_one(".article-video video")
        assert article_video.select_one("source")["src"] == entry["src"]
        assert article_video.select_one("track")["src"] == entry["captions"]
    for slug in WATCH:
        watch = page(watch_path(slug))
        v = json.loads(watch.select_one('script[type="application/ld+json"]').string)["@graph"][0]
        assert {a["href"] for a in watch.select("[data-watch-offset]")} == {c["url"].removeprefix(SITE + watch_path(slug)) for c in v["hasPart"]}
        assert len(v["hasPart"]) == 5 and len({c["startOffset"] for c in v["hasPart"]}) == 5
        assert watch.select_one('meta[property="og:image"]')["content"] == v["thumbnailUrl"][0]
    verify_calendar_archive(calendar)
    verify_legacy_tag_pages()
    for i in range(2, (len(articles) + 9)//10 + 1):
        alias, primary = page(f"/page/{i}/"), page(f"/archives/page/{i}/")
        assert alias.select_one('link[rel=canonical]')["href"] == SITE + f"/archives/page/{i}/"
        assert [a["href"] for a in alias.select(".post-list .row-title")] == [a["href"] for a in primary.select(".post-list .row-title")]
    for img in home.select(".front-media img[srcset]"):
        for part in img["srcset"].split(","):
            path, width = part.split()
            assert target(path).stat().st_size <= target(img["src"]).stat().st_size
            if path.startswith("/images/article-covers/"):
                assert dimensions(path, ROOT)[0] == int(width[:-1])
    print(f"OK: {len(expected)} Xiaoxiao library entries; 25-series navigation; exact archive alias consolidation; footer contacts.")
    assert sum(guide_counts.values()) == len(articles)
    print("OK: cited article reading leads: " + ", ".join(f"{k}={v}" for k, v in sorted(guide_counts.items())))
    print(f"OK: {len(paths)} canonical sitemap routes; {len(articles)} articles; 5 evidence cards; 3 complete watch transcripts.")


if __name__ == "__main__":
    main()
