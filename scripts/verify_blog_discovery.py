# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4==4.15.0", "lxml==6.1.3"]
# ///
"""Verify the generated discovery contract and optionally compare protected content."""
import argparse
import json
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from blog_discovery import EVIDENCE, WATCH, watch_path
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

    for article in articles:
        path = "/article/" + article.name
        markup = page(path)
        data = json.loads(markup.select_one('script[type="application/ld+json"]').string)["@graph"]
        assert [v["@type"] for v in data] == ["BlogPosting", "BreadcrumbList"], path
        headline = markup.select_one("h1.post-title").get_text(strip=True)
        assert data[0]["headline"] == headline and data[0]["author"]["name"] == markup.select_one(".post-author").get_text(strip=True)
        card = markup.select_one(".article-main > .editorial-evidence")
        assert bool(card) == (article.stem in EVIDENCE), path
        if card:
            assert len(card.select("dd")) == 3 and not markup.select_one(".post-body .editorial-evidence"), path
        if args.baseline:
            previous = old_page(args.baseline, path)
            assert previous.select_one(".post-body").decode_contents() == markup.select_one(".post-body").decode_contents(), path
            assert str(previous.select_one(".article-video")) == str(markup.select_one(".article-video")), path

    for slug in WATCH:
        markup = page(watch_path(slug))
        source_url = markup.select_one("video source")["src"]
        cap = markup.select_one("video track")["src"]
        data = json.loads(markup.select_one('script[type="application/ld+json"]').string)["@graph"][0]
        assert data["@type"] == "VideoObject" and data["contentUrl"] == source_url
        sitemap_entry = next(entry for entry in sitemap.findall("map:url", NS) if entry.findtext("map:loc", namespaces=NS) == SITE + watch_path(slug))
        assert sitemap_entry.findtext("video:video/video:publication_date", namespaces=NS) == data["uploadDate"]
        assert sitemap_entry.findtext("video:video/video:content_loc", namespaces=NS) == source_url
        cues = [line for line in target(cap).read_text().splitlines() if line and " --> " not in line and line != "WEBVTT"]
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
    assert must_email not in profile.select_one('script[type="application/ld+json"]').string
    if args.baseline:
        assert old_page(args.baseline, "/about/").select_one(".post-body").decode_contents() == profile.select_one(".post-body").decode_contents()
    demo_prefix = "/videos/portfolio/ai-test-cases-demo-v2"
    demo_files = [demo_prefix + suffix for suffix in (".mp4", ".webp", ".zh-CN.vtt")]
    demo_exists = all(target(path).is_file() and target(path).stat().st_size for path in demo_files)
    demo = profile.select_one("#ai-test-cases figure.work-demo")
    assert bool(demo) == demo_exists
    if demo:
        assert demo.select_one("figcaption").get_text(strip=True) == "完整版实录｜Skill、MCP 与用例导出 · 虚构需求、本地模拟模型"
        media = demo.select_one("video")
        assert (media["width"], media["height"], media["preload"], media["poster"]) == ("1440", "900", "none", demo_files[1])
        assert "controls" in media.attrs and "playsinline" in media.attrs and "autoplay" not in media.attrs
        assert media.select_one("source")["src"] == demo_files[0]
        captions = media.select_one("track")
        assert captions["src"] == demo_files[2] and captions["srclang"] == "zh-CN" and "default" not in captions.attrs
        assert target(demo_files[2]).read_text().startswith("WEBVTT")
        assert demo.select_one("a[download]")["href"] == demo_files[0]
    assert not tool.select_one(f'a[href="{must_email}"]')
    assert "/videos/" in paths
    library = page("/videos/")
    manifest = json.loads((ROOT / "scripts/article_videos.json").read_text())
    expected = {watch_path(Path(p).stem) if Path(p).stem in WATCH else p + "#article-video-title"
                for p,v in manifest.items() if v.get("voice") == "zh-CN-XiaoxiaoNeural" and v.get("poster") and v.get("captions")}
    all_links = {a["href"] for a in library.select(".video-shelf li a[href]")}
    assert all_links == expected and library.select_one("h1").get_text(strip=True) == "视频讲解目录"
    for item in json.loads((ROOT / "scripts/series_catalog.json").read_text()):
        series_url = f"/series/{item['id']}/"
        series_pg = page(series_url)
        assert series_pg.select_one('.article-path a[href="/"]')
        assert series_pg.select_one(f'.article-path a[href="/series/#topic-{item["section"]}"]')
        video_link = series_pg.select_one('.series-start-links a[href^="/videos/#"]')
        if video_link:
            assert library.find(id=video_link["href"].split("#",1)[1]), series_url
    for slug in WATCH:
        watch = page(watch_path(slug))
        v = json.loads(watch.select_one('script[type="application/ld+json"]').string)["@graph"][0]
        assert {a["href"] for a in watch.select("[data-watch-offset]")} == {c["url"].removeprefix(SITE + watch_path(slug)) for c in v["hasPart"]}
        assert len(v["hasPart"]) == 5 and len({c["startOffset"] for c in v["hasPart"]}) == 5
        assert watch.select_one('meta[property="og:image"]')["content"] == v["thumbnailUrl"][0]
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
    print(f"OK: {len(paths)} canonical sitemap routes; {len(articles)} articles; 5 evidence cards; 3 complete watch transcripts.")


if __name__ == "__main__":
    main()
