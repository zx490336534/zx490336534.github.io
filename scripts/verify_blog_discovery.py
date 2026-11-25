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
    print(f"OK: {len(paths)} canonical sitemap routes; {len(articles)} articles; 5 evidence cards; 3 complete watch transcripts.")


if __name__ == "__main__":
    main()
