"""Ordered reading paths, independent of blog publication dates."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from build_blog import Post


CATALOG_SECTIONS = {
    "testing": "测试与质量",
    "ai": "AI 工程",
    "development": "开发与项目",
    "engineering": "工程工具",
    "notes": "学习记录",
}


@dataclass
class ReadingSeries:
    slug: str
    title: str
    section: str
    description: str
    audience: str
    featured: bool
    groups: list[tuple[str, list[Post]]]
    chapters: list[Post]
    resource: dict | None = None

    @property
    def url(self):
        return f"/series/{self.slug}/"


def load_series(posts, source):
    post_by_path = {post.path: post for post in posts}
    collection = []
    positions = {}
    slugs = set()
    for item in json.loads(source.read_text()):
        slug = item["id"]
        if not re.fullmatch(r"[a-z0-9-]+", slug) or slug in slugs:
            raise ValueError(f"无效或重复的系列标识 {slug}")
        slugs.add(slug)
        section = item["section"]
        if section not in CATALOG_SECTIONS:
            raise ValueError(f"无效的系列主题 {slug} {section}")

        groups = []
        chapters = []
        ordered = set()
        for part in item["groups"]:
            group = []
            for path in part["chapters"]:
                post = post_by_path.get(path)
                if post is None or path in ordered or not post.title.strip():
                    raise ValueError(f"无效或重复的系列文章 {slug} {path}")
                ordered.add(path)
                group.append(post)
            if not group:
                raise ValueError(f"系列章节为空 {slug} {part['title']}")
            groups.append((part["title"], group))
            chapters.extend(group)
        if len(chapters) < 4:
            raise ValueError(f"系列至少需要 4 篇文章 {slug}")

        series = ReadingSeries(
            slug, item["title"], section, item["description"], item["audience"], item["featured"], groups, chapters, item.get("resource")
        )
        collection.append(series)
        for number, post in enumerate(chapters, 1):
            positions.setdefault(post.path, (series, number))
    return collection, positions


def cards(collection, thumbnail):
    cards = []
    for series in collection:
        first = series.chapters[0]
        cards.append(
            f'<article class="series-card"><a class="series-card-link" href="{series.url}">'
            f'{thumbnail(first)}<div class="series-card-copy"><h3>{escape(series.title)}</h3>'
            f'<p>{escape(series.description)}</p>'
            f'<span class="series-card-meta">{len(series.chapters)} 篇 · 从「{escape(first.title)}」开始</span>'
            '</div></a></article>'
        )
    return '<div class="series-grid">' + "".join(cards) + '</div>'


def catalog_page(collection, thumbnail):
    chapters = sum(len(series.chapters) for series in collection)
    shortcuts = []
    sections = []
    for section, label in CATALOG_SECTIONS.items():
        members = [series for series in collection if series.section == section]
        if not members:
            continue
        anchor = f"topic-{section}"
        shortcuts.append(f'<a href="#{anchor}">{escape(label)}</a>')
        sections.append(
            f'<section class="series-stage" id="{anchor}" aria-labelledby="{anchor}-heading">'
            f'<h2 id="{anchor}-heading">{escape(label)}</h2>{cards(members, thumbnail)}</section>'
        )
    return f'''<section class="listing series-library">
  <header class="page-heading"><div><h1>系列阅读</h1><p>{len(collection)} 个系列 · {chapters} 篇文章</p></div>
    <a href="/categories/">按分类浏览 ↗</a></header>
  <nav class="series-stage-links" aria-label="系列主题">{"".join(shortcuts)}</nav>
  {"".join(sections)}
</section>'''


def series_page(series, thumbnail):
    first = series.chapters[0]
    resources = ""
    if series.resource:
        url = escape(series.resource["url"])
        label = escape(series.resource["title"])
        resources = f'<a class="series-tool" href="{url}">{label} ↗</a>'
    stages = []
    shortcuts = []
    number = 1
    for stage, (label, chapters) in enumerate(series.groups, 1):
        title = escape(label)
        anchor = f"stage-{stage}"
        shortcuts.append(f'<a href="#{anchor}">{title}</a>')
        rows = []
        first_number = number
        for post in chapters:
            rows.append(
                f'<li id="chapter-{number}"><a href="{escape(post.path)}" class="series-chapter-link">'
                '<span class="list-rank" aria-hidden="true"></span>'
                f'{thumbnail(post)}<strong>{escape(post.title)}</strong></a></li>'
            )
            number += 1
        stages.append(
            f'<section class="series-stage" id="{anchor}"><h2>{title}</h2>'
            f'<ol class="series-chapters" role="list" start="{first_number}">{"".join(rows)}</ol></section>'
        )
    jump = ('<nav class="series-stage-links" aria-label="阅读阶段">' + "".join(shortcuts) + '</nav>') if len(stages) > 1 else ""

    return f'''<section class="listing series-page">
  <nav class="article-path" aria-label="系列位置"><a href="/series/">系列阅读</a> <span aria-hidden="true">/</span> <span aria-current="page">{escape(series.title)}</span></nav>
  <header class="page-heading"><div><h1>{escape(series.title)}</h1><p>{escape(series.description)}</p></div>
    <span class="series-size">{len(series.chapters)} 篇</span></header>
  <div class="series-start">
    <p><strong>适合</strong> {escape(series.audience)}</p>
    <div class="series-start-links">
      <a class="series-start-link" href="{escape(first.path)}">读第一篇 · {escape(first.title)} ↗</a>
      {resources}
    </div>
  </div>
  {jump}
  {"".join(stages)}
</section>'''


def position_link(position):
    if position is None:
        return ""
    series, number = position
    return (
        f'<a class="series-progress" href="{series.url}#chapter-{number}">'
        f'{escape(series.title)} · 第 {number}/{len(series.chapters)} 篇</a>'
    )


def chapter_title(post, number):
    return f"第 {number:02d} 篇｜{post.title}"


def article_navigation(position):
    series, number = position
    directory = f'<h2><a href="{series.url}">查看系列目录 ↗</a></h2>'
    neighbors = []
    for index, label in ((number - 2, "同系列上一篇"), (number, "同系列下一篇")):
        if 0 <= index < len(series.chapters):
            post = series.chapters[index]
            neighbors.append(f'<a href="{escape(post.path)}"><small>{label}</small>{escape(chapter_title(post, index + 1))}</a>')
    return ('<section class="series-continuation">' + directory
            + '<nav class="related" aria-label="同系列文章">' + "".join(neighbors) + '</nav></section>')
