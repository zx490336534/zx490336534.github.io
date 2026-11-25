"""Public discovery of article provenance, tested media, and related material."""
from collections import defaultdict
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

from blog_discovery import WATCH, json_ld, watch_path


@lru_cache(maxsize=None)
def dimensions(path, root):
    if not path.startswith("/images/article-covers/") or not path.endswith(".webp"):
        return None
    with (root / path.lstrip("/")).open("rb") as handle:
        b = handle.read(32)
    if b[:4] != b"RIFF" or b[8:12] != b"WEBP":
        return None
    encoding = b[12:16]
    if encoding == b"VP8X":
        return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
    if encoding == b"VP8L" and b[20] == 0x2f:
        data = int.from_bytes(b[21:25], "little")
        return 1 + (data & 0x3fff), 1 + ((data >> 14) & 0x3fff)
    if encoding == b"VP8 " and b[23:26] == b"\x9d\x01\x2a":
        return int.from_bytes(b[26:28], "little") & 0x3fff, int.from_bytes(b[28:30], "little") & 0x3fff
    return None


def cover_dimensions(path, root):
    return f' width="{size[0]}" height="{size[1]}"' if (size := dimensions(path, root)) else ""


def cover_attributes(path, root, sizes):
    if not (size := dimensions(path, root)):
        return ""
    sources = []
    for width in (384, 768):
        alternate = f"/images/cover-variants/{width}/{Path(path).name}"
        if (root / alternate.lstrip("/")).is_file():
            sources.append(f"{alternate} {width}w")
    sources.append(f"{path} {size[0]}w")
    alt_attrs = (' srcset="' + escape(", ".join(sources)) + '" sizes="' + escape(sizes) + '"') if len(sources) > 1 else ""
    return cover_dimensions(path, root) + alt_attrs


def source_panel(post):
    """Point to real on-page reference sections and keep original WeChat sources."""
    is_wechat = post.source and urlsplit(post.source).hostname == "mp.weixin.qq.com"
    references = [(anchor, title) for anchor, title in post.toc if title.strip(" ：:") in {
        "参考", "参考资料", "参考链接", "参考文献", "参考文档", "相关资料", "相关链接", "扩展阅读", "References",
    }]
    if not is_wechat and not references:
        return ""
    links = "".join(f'<li><a href="#{quote(anchor, safe="")}">{escape(title)}（本文）</a></li>' for anchor, title in references)
    if is_wechat:
        links += f'<li><a class="source-link" href="{escape(post.source)}">查看微信公众号原文 ↗</a></li>'
    return ('<aside class="source-panel" aria-labelledby="article-sources-title">'
            '<h2 id="article-sources-title">来源与参考</h2><ul>' + links + '</ul></aside>')


def series_metadata(series, site):
    path = series.url
    summary = f"{series.description} {len(series.chapters)} 篇，适合{series.audience}。"
    data = json_ld(
        {"@type": "CollectionPage", "name": series.title, "description": summary,
         "url": site + path, "inLanguage": "zh-CN"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": site + "/"},
            {"@type": "ListItem", "position": 2, "name": "系列阅读", "item": site + "/series/"},
            {"@type": "ListItem", "position": 3, "name": series.title, "item": site + path},
        ]},
    )
    return summary, data


def video_library(posts, series, positions, site):
    published = [
        post for post in posts
        if post.video and post.video.get("voice") == "zh-CN-XiaoxiaoNeural"
        and post.video.get("captions") and post.video.get("poster")
    ]
    by_series = defaultdict(list)
    other = defaultdict(list)
    for post in published:
        if post.path in positions:
            series_item, number = positions[post.path]
            by_series[series_item.slug].append((number, post))
        else:
            trail = post.topic.trail() if post.topic else []
            other[(trail[0].key, trail[0].name) if trail else ("other", "其他文章")].append(post)
    groups = []
    for item in series:
        if entries := by_series.get(item.slug):
            groups.append((f"videos-{item.slug}", item.title, item.url,
                           [p for _, p in sorted(entries, key=lambda r: r[0])]))
    for (key, topic), entries in other.items():
        groups.append((f"topic-videos-{key}", topic, "", entries))

    def row(post):
        stem = Path(post.path).stem
        href = watch_path(stem) if stem in WATCH else post.path + "#article-video-title"
        sec = post.video["duration"]
        return (f'<li><a href="{escape(href)}">{escape(post.display_title)}</a>'
                f'<time datetime="PT{sec}S">{sec // 60}:{sec % 60:02}</time></li>')

    nav = "".join(f'<a href="#{anchor}">{escape(title)} <small>{len(entries)}</small></a>' for anchor, title, _, entries in groups)
    blocks = []
    for anchor, title, link, entries in groups:
        related = f'<a href="{escape(link)}">看系列目录 →</a>' if link else ""
        blocks.append(
            f'<section class="video-shelf" id="{anchor}" aria-labelledby="{anchor}-heading">'
            f'<header class="section-title"><h2 id="{anchor}-heading">{escape(title)}</h2>{related}</header>'
            f'<ul>{"".join(row(p) for p in entries)}</ul></section>'
        )
    description = "按主题和系列查找测试游记的实战讲解。每支使用 Edge 晓晓普通话配音并附简体中文字幕。"
    data = json_ld({
        "@type": "CollectionPage", "name": "视频讲解目录", "url": site + "/videos/",
        "description": description, "inLanguage": "zh-CN",
    })
    featured = "".join(row(p) for p in published if Path(p.path).stem in WATCH)
    return (
        '<section class="listing video-library"><header class="page-heading"><div><h1>视频讲解目录</h1>'
        f'<p>{escape(description)} · {len(published)} 支</p></div><a href="/series/">从系列开始 ↗</a></header>'
        f'<section class="video-shelf"><h2>独立观看页与文字稿</h2><ul>{featured}</ul></section>'
        f'<nav class="series-stage-links" aria-label="跳到视频系列或主题">{nav}</nav>'
        + "".join(blocks) + "</section>", description, data
    )
