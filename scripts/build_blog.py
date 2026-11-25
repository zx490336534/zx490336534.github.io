# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4==4.15.0", "lxml==6.1.3", "nh3==0.3.8"]
# ///
"""Render the published HTML archive in place: uv run scripts/build_blog.py."""

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from html import escape, unescape
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import nh3

from blog_topics import Topic, browser_page, links as taxonomy_links, read_catalog, topic_trail

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://www.zhongxin.website"
UMAMI_WEBSITE_ID = "1b24a540-f89e-43de-bf0f-d783133d4a28"
NAME = "测试游记"
GISCUS_REPO = "zx490336534/zx490336534.github.io"
GISCUS_REPO_ID = "MDEwOlJlcG9zaXRvcnkzNDQwOTE0MTc="
GISCUS_CATEGORY = "文章评论"
GISCUS_CATEGORY_ID = "DIC_kwDOFIJrGc4DL60Q"
DESCRIPTION = "听白的技术博客，记录测试开发、自动化与 AI 工程实践。"
ALLOWED_TAGS = set("a abbr b blockquote br caption code col colgroup dd del details div dl dt em figcaption figure h1 h2 h3 h4 h5 h6 hr i img kbd li mark ol p pre s section small span strong sub summary sup table tbody td th thead tfoot tr u ul".split())
ALLOWED_ATTRIBUTES = {
    "*": {"id", "class"}, "a": {"href", "title"},
    "img": {"src", "alt", "width", "height", "loading", "decoding", "referrerpolicy"},
    "td": {"rowspan", "colspan"}, "th": {"rowspan", "colspan", "scope"},
    "ol": {"start", "reversed"}, "li": {"value"}, "details": {"open"},
}


def html(value):
    return escape(str(value), quote=True)


def normalized_path(value):
    path = unquote(urlsplit(value).path)
    return quote(path, safe="/!$&'()*+,-.;=:@_")


def compact(text):
    return " ".join(text.split())


@dataclass
class Post:
    path: str
    title: str
    published: str
    body: str
    description: str
    categories: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    source: str = ""
    cover: str = ""
    toc: list = field(default_factory=list)
    search_text: str = ""
    legacy_comments: bool = False
    author: str = "听白"
    topic: Topic | None = None
    editorial_tags: list = field(default_factory=list)

    @property
    def day(self):
        return self.published[:10]


def prepare_body(body, title):
    first = body.find(re.compile(r"^h[1-6]$"))
    if (first and first is body.find(recursive=False)
            and compact(first.get_text(" ", strip=True)).casefold() == title.casefold()):
        if first.get("id"):
            first.name = "span"
            first.clear()
        else:
            first.decompose()
    headings = []
    ids = {node['id'] for node in body.find_all(id=True)}
    for heading in body.find_all(re.compile(r"^h[1-6]$")):
        label = compact(heading.get_text(" ", strip=True))
        if not label:
            continue
        if not heading.get("id"):
            base = re.sub(r"[^\w-]+", "-", label).strip("-") or "section"
            anchor = base
            suffix = 2
            while anchor in ids:
                anchor = f"{base}-{suffix}"
                suffix += 1
            heading["id"] = anchor
            ids.add(anchor)
        if heading.name in {"h1", "h2", "h3"}:
            headings.append((heading["id"], label))
    for table in body.find_all("table"):
        if table.find_parent("figure", class_="highlight") or table.find_parent(class_="table-scroll"):
            continue
        wrapper = body.new_tag("div", attrs={"class": "table-scroll", "tabindex": "0", "role": "region", "aria-label": "数据表格"})
        table.wrap(wrapper)
    for image in body.find_all("img", src=True):
        image["loading"] = "lazy"
        image["decoding"] = "async"
        image.attrs.setdefault("alt", "")
        if (urlsplit(image["src"]).hostname or "").endswith(".sinaimg.cn"):
            image["referrerpolicy"] = "no-referrer"
    return headings


def read_post(path):
    page = BeautifulSoup(path.read_text(), "lxml")
    body = page.select_one(".post-body")
    title = page.select_one(".post-title")
    published = page.select_one('time[itemprop~="datePublished"]')
    if body is None or title is None or published is None:
        raise ValueError(f"缺少正文、标题或日期 {path.name}")
    description = page.select_one('meta[name="description"]')
    source = page.select_one("a.source-link")
    cover = page.select_one('meta[name="blog-cover"]')
    author = page.select_one(".post-author")
    tag_metadata = page.select_one(".legacy-tags") or page.select_one(".post-tags")
    title = title.get_text(strip=True)
    toc = prepare_body(body, title)
    summary = compact(description.get("content", "") if description else "")
    if summary.startswith(title + " "):
        summary = summary[len(title):].strip()
    return Post(
        "/" + path.relative_to(ROOT).as_posix(), title, published["datetime"],
        body.decode_contents().strip(),
        summary or compact(body.get_text(" ", strip=True))[:150],
        [(a.get_text(strip=True), normalized_path(a["href"])) for a in page.select(".post-category a[href]")],
        [(a.get_text(strip=True).removeprefix("#").strip(), normalized_path(a["href"])) for a in (tag_metadata.select("a[href]") if tag_metadata else [])],
        source["href"] if source else "", cover["content"] if cover else "", toc,
        compact(body.get_text(" ", strip=True)), bool(page.select_one("#disqus_thread")),
        author.get_text(strip=True) if author else "听白",
    )


def import_posts(path, posts):
    existing = {post.path: post for post in posts}
    for item in json.loads(path.read_text()):
        route = item['path']
        if not re.fullmatch(r"/article/[a-z0-9-]+\.html", route):
            raise ValueError(f"不支持的文章地址 {route}")
        source = urlsplit(item["source"])
        if source.scheme != "https" or source.netloc != "mp.weixin.qq.com" or not source.path.startswith("/s"):
            raise ValueError(f"无效的公众号原文地址 {route}")
        clean = nh3.clean(item["body"], tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                          url_schemes={"https", "http", "mailto"}, clean_content_tags={"script", "style", "iframe", "object", "noscript"})
        document = BeautifulSoup(clean, "lxml")
        if not document.body or not document.body.get_text(strip=True):
            raise ValueError(f"公众号正文为空 {route}")
        body = document.body
        previous = existing.get(route)
        title = previous.title if previous else item['title']
        toc = prepare_body(body, title)
        search_text = compact(body.get_text(" ", strip=True))
        cover = item.get("cover", "")
        if cover and not re.fullmatch(r"/images/blog-media/[a-f0-9]+\.(?:webp|gif|png|svg)", cover):
            raise ValueError(f"无效的本地封面 {route}")
        published = item['published']
        date.fromisoformat(published[:10])
        if previous:
            # Keep historical fragment links even if the restored edition used different headings.
            restored_ids = {node['id'] for node in body.find_all(id=True)}
            previous_body = BeautifulSoup(previous.body, "lxml")
            old_ids = [node['id'] for node in previous_body.find_all(id=True) if node['id'] not in restored_ids]
            for old_id in reversed(list(dict.fromkeys(old_ids))):
                label = next((label for anchor, label in previous.toc if anchor == old_id), None)
                target = next((body.find(id=anchor) for anchor, text in toc if text == label), None) if label else None
                alias = document.new_tag("span", id=old_id)
                if target:
                    target.insert_before(alias)
                else:
                    body.insert(0, alias)
        existing[route] = Post(
            route, title, previous.published if previous else published,
            body.decode_contents().strip(), (item.get('description') or search_text)[:170],
            previous.categories if previous else [("公众号", "/categories/%E5%85%AC%E4%BC%97%E5%8F%B7/")],
            previous.tags if previous else [], item['source'], cover, toc, search_text,
            previous.legacy_comments if previous else False, item.get("author") or "听白",
        )
    return list(existing.values())


def analytics_script():
    return (f'<script id="site-analytics" src="/js/site-analytics.js" '
            f'data-website-id="{UMAMI_WEBSITE_ID}" defer></script>')


def add_analytics_to_resources():
    readers = [
        ROOT / "tools/test-cases/index.html",
        *(ROOT / "teaching-aihom").rglob("*.html"),
        *(ROOT / "teaching-kuai").rglob("*.html"),
    ]
    for file in readers:
        page = file.read_text()
        if 'id="site-analytics"' in page:
            updated = re.sub(r'<script id="site-analytics"[^>]*></script>', analytics_script(), page, count=1)
        else:
            updated, count = re.subn(r"</head>", "  " + analytics_script() + "\n</head>", page, count=1, flags=re.I)
            if count != 1:
                raise ValueError(f"缺少页面头部 {file.relative_to(ROOT)}")
        if updated != page:
            file.write_text(updated)


def shell(title, path, content, description=DESCRIPTION, extra_head=""):
    title_tag = NAME if path == "/" else f"{title} · {NAME}"
    nav = [("归档", "/archives/"), ("分类", "/categories/"), ("工具与课程", "/lab/"), ("关于", "/about/")]
    links = []
    for label, url in nav:
        current = ' aria-current="page"' if url == path else ""
        if not current and (path.startswith(url) or (path.startswith("/article/") and url == "/archives/")):
            current = ' aria-current="location"'
        links.append(f'<a href="{url}"{current}>{label}</a>')
    links_html = "".join(links)
    canonical = html(SITE + path)
    summary = excerpt(description, 180)
    counts = '\n  <script src="/js/public-counts.js" defer></script>' if path == "/" or path.startswith("/article/") else ""
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{html(title_tag)}</title>
  <meta name="description" content="{summary}">
  <meta property="og:title" content="{html(title_tag)}">
  <meta property="og:description" content="{summary}">
  <meta property="og:url" content="{canonical}">
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" href="/atom.xml" type="application/atom+xml" title="测试游记">
  <link rel="icon" href="/images/avatar.jpeg">
  <script src="/js/appearance.js"></script>
  <link rel="stylesheet" href="/css/blog.css">
  <script src="/js/blog.js" defer></script>
  {analytics_script()}{counts}
  {extra_head}
</head>
<body>
  <a class="skip-link" href="#main">跳到正文</a>
  <header class="masthead">
    <div class="wrap masthead-inner">
      <a class="wordmark" href="/">测试游记<span>听白</span></a>
      <nav aria-label="主导航">{links_html}</nav>
      <div class="masthead-actions">
        <label class="visually-hidden" for="site-appearance">外观</label>
        <select id="site-appearance" class="site-appearance" hidden>
          <option value="system">外观 · 系统</option>
          <option value="light">外观 · 浅色</option>
          <option value="dark">外观 · 深色</option>
        </select>
        <button type="button" data-open-search class="search-trigger">搜索 <kbd>⌘/Ctrl K</kbd></button>
      </div>
    </div>
  </header>
  <main id="main" class="wrap">{content}</main>
  <footer class="wrap footer">
    <a class="footer-brand" href="/">测试游记<span>听白的技术博客</span></a>
    <nav aria-label="页脚导航">
      <a href="/archives/">文章归档</a><a href="/tags/">标签</a><a href="/lab/">工具与课程</a><a href="/atom.xml">RSS</a>
    </nav>
  </footer>
  <dialog id="search-dialog" aria-labelledby="search-title">
    <div class="search-heading"><h2 id="search-title">搜索文章</h2><form method="dialog"><button>关闭</button></form></div>
    <label class="visually-hidden" for="article-search">搜索标题、主题、标签或正文</label>
    <input id="article-search" type="search" placeholder="搜索标题、分类、标签或正文…" autocomplete="off" maxlength="100" autofocus>
    <p id="search-status" role="status"></p>
    <ol id="search-results"></ol>
  </dialog>
</body>
</html>
'''


def date_label(post):
    return f'<time datetime="{html(post.published)}">{html(post.day)}</time>'


def public_counter(metric, label, article_path=None):
    path = f' data-article-path="{html(article_path)}"' if article_path else ""
    return (f'<span class="public-counter" data-public-count="{metric}"{path} hidden>'
            f'<span>{label}</span> <strong></strong></span>')


def category_links(post):
    if post.topic:
        return taxonomy_links([(post.topic.name, post.topic.url)])
    return taxonomy_links(post.categories)


def excerpt(description, limit):
    # WeChat descriptions can carry escaped HTML entities from their page metadata.
    text = unescape(re.sub(r"\\x26(?=(?:[a-zA-Z]+|#[xX]?[0-9a-fA-F]+);)", "&", description))
    return html(text[:limit])


def post_rows(posts, *, show_category=True):
    css = "post-list" if show_category else "post-list without-category"
    return f'<ul class="{css}">' + "".join(
        f'<li>{date_label(post)}<div><a class="row-title" href="{html(post.path)}">{html(post.title)}</a>'
        f'<p>{excerpt(post.description, 110)}</p></div>'
        + (f'<span class="categories">{category_links(post)}</span>' if show_category else "")
        + "</li>"
        for post in posts
    ) + "</ul>"


def home_picture(post):
    authored_cover = f"/images/blog-covers/{Path(post.path).stem}.webp"
    for path in (authored_cover, post.cover):
        if path.startswith("/images/") and (ROOT / path.lstrip("/")).is_file():
            return path
    for img in BeautifulSoup(post.body, "lxml").select("img[src][width][height]"):
        width, height = str(img["width"]), str(img["height"])
        if not (width.isdigit() and height.isdigit()):
            continue
        path = img["src"]
        if (int(width) >= 560 and int(height) >= 240 and int(width) >= int(height)
                and path.startswith("/images/blog-media/") and Path(path).suffix in {".webp", ".jpg", ".png"}
                and (ROOT / path.lstrip("/")).is_file()):
            return path
    return ""


RESOURCES = [
    ("在线工具", "测试用例脑图生成器", "把需求整理成测试点和用例，在脑图里查看和编辑。", f"{SITE}/tools/test-cases/"),
    ("课程地图", "AIHom 全栈学习地图", "按模块了解前端、后端、Agent 和布局链路。", "/teaching-aihom/lessons/index.html"),
    ("课程地图", "Kuai 测试平台学习地图", "从三仓基础读到测试平台的核心功能和实战。", "/teaching-kuai/lessons/index.html"),
]


def resource_cards():
    return '<div class="resource-grid">' + "".join(
        f'<a class="resource-card" href="{html(url)}"><span>{html(kind)}</span>'
        f'<strong>{html(title)}</strong><p>{html(summary)}</p></a>'
        for kind, title, summary, url in RESOURCES
    ) + "</div>"


def home_story(post, picture, lead=False):
    heading = "h2" if lead else "h3"
    priority = 'fetchpriority="high"' if lead else 'loading="lazy"'
    image = (
        f'<div class="front-media"><img src="{html(picture)}" alt="" decoding="async" {priority}></div>'
        if picture else ""
    )
    meta = post.topic.trail()[0].name if post.topic and post.topic.trail() else ""
    label = f'<span>{html(meta)}</span>' if meta else ""
    action = '<span class="front-read">阅读全文 <span aria-hidden="true">↗</span></span>' if lead else ""
    layout = "front-lead" if lead else "front-card"
    with_picture = " with-picture" if picture else ""
    return f'''<article class="{layout}">
      <a href="{html(post.path)}" class="front-story{with_picture}">
        {image}
        <div class="front-copy">
          <div class="front-meta">{label}{date_label(post)}</div>
          <{heading}>{html(post.title)}</{heading}>
          <p>{excerpt(post.description, 150)}</p>
          {action}
        </div>
      </a>
    </article>'''


def home(posts, catalog):
    feature = posts[0]
    photos = []
    for post in posts[1:40]:
        picture = home_picture(post)
        if picture:
            photos.append((post, picture))
        if len(photos) == 8:
            break

    gallery = "".join(home_story(post, picture) for post, picture in photos)
    illustrated = f'''
  <section class="section" aria-labelledby="illustrated-title">
    <header class="section-title"><h2 id="illustrated-title">图文选读</h2><a href="/archives/">文章归档 ↗</a></header>
    <div class="front-gallery">{gallery}</div>
  </section>''' if gallery else ""
    paths = "".join(
        f'<a href="{child.url}"><strong>{html(child.name)}</strong><small>{len(child.members)} 篇</small></a>'
        for child in catalog.children
    )
    featured = {post.path for post, _ in photos}
    recent = [post for post in posts[1:] if post.path not in featured][:7]
    content = f'''
  <header class="publication-heading">
    <div>
      <h1>测试开发与 AI 工程实践</h1>
      <p>听白的技术博客</p>
      {public_counter("clicks", "近 30 天全站点击")}
    </div>
    <div class="publication-actions">
      <a class="solid-link" href="/categories/">浏览分类 <span aria-hidden="true">↗</span></a>
      <a href="/lab/">工具与课程 <span aria-hidden="true">↗</span></a>
    </div>
  </header>
  <section class="publication-feature" aria-label="最新文章">
    {home_story(feature, home_picture(feature), lead=True)}
  </section>
  <nav class="publication-topics" aria-label="主要分类">{paths}</nav>
  {illustrated}
  <section class="section" aria-labelledby="recent-title">
    <header class="section-title"><h2 id="recent-title">近期文章</h2><a href="/archives/">全部文章 ↗</a></header>
    {post_rows(recent)}
  </section>
  <section class="section" id="courses" aria-labelledby="tools-title">
    <header class="section-title"><h2 id="tools-title">工具与课程</h2><a href="/lab/">前往工具页 ↗</a></header>
    {resource_cards()}
  </section>'''
    return shell(NAME, "/", content)


def reading_time(post):
    words = len(re.findall(r"[A-Za-z0-9]+", post.search_text))
    characters = len(re.findall(r"[\u3400-\u9fff]", post.search_text))
    minutes = max(1, round(words / 220 + characters / 450))
    return f"约 {minutes} 分钟"


def article(post, older, newer):
    toc = "".join(f'<li><a href="#{quote(anchor, safe="")}">{html(label)}</a></li>' for anchor, label in post.toc)
    outline = f'<aside class="outline"><details open><summary>本文目录</summary><ol>{toc}</ol></details></aside>' if toc else ''
    tags = taxonomy_links(post.editorial_tags or post.tags)
    original_tags = taxonomy_links(post.tags)
    original_categories = taxonomy_links(post.categories)
    trail = topic_trail(post.topic) if post.topic else original_categories
    source = f'<p class="source"><a class="source-link" href="{html(post.source)}">查看微信公众号原文 ↗</a></p>' if post.source else ''
    related = "".join(f'<a href="{html(link.path)}"><small>{direction}</small>{html(link.title)}</a>'
                      for link, direction in [(newer, "较新文章"), (older, "较早文章")] if link)
    legacy_anchor = (
        f'<div id="disqus_thread" data-identifier="{html(post.path.lstrip("/"))}" hidden></div>'
        if post.legacy_comments else ""
    )
    comments = f'''<section class="article-comments" id="comments" aria-labelledby="comments-title"
          data-repo="{GISCUS_REPO}" data-repo-id="{GISCUS_REPO_ID}"
          data-category="{GISCUS_CATEGORY}" data-category-id="{GISCUS_CATEGORY_ID}" data-article-path="{html(post.path)}">
          {legacy_anchor}
          <h2 id="comments-title">评论与讨论</h2>
          <p>使用 GitHub 账号留言，评论公开显示。</p>
          <div class="comment-actions">
            <button type="button" data-open-comments>打开评论</button>
            <a href="https://github.com/{GISCUS_REPO}/discussions">GitHub 讨论区 ↗</a>
          </div>
          <p role="status"></p>
          <div class="giscus"></div>
        </section>'''
    cover = f'<meta name="blog-cover" content="{html(post.cover)}"><meta property="og:image" content="{html(SITE + post.cover)}">' if post.cover else ''
    content = f'''
  <article class="article">
    <header class="article-header">
      <nav class="article-path" aria-label="文章分类"><a href="/categories/">分类</a> <span aria-hidden="true">/</span> {trail}</nav>
      <h1 class="post-title">{html(post.title)}</h1>
      <div class="entry-meta"><span class="post-author">{html(post.author)}</span><time itemprop="datePublished" datetime="{html(post.published)}">{html(post.day)}</time>
        <span class="post-category" hidden>{original_categories}</span>
        <span class="read-time">{reading_time(post)}</span>
        {public_counter("reads", "近 30 天阅读", post.path)}
        <a href="#comments" data-jump-comments>评论</a></div>
    </header>
    <div class="article-layout {'with-outline' if outline else ''}">
      {outline}
      <div class="article-main">
        <div class="post-body">{post.body}</div>
        {source}
        <div class="post-tags" aria-label="文章标签">{tags}</div>
        <div class="legacy-tags" hidden>{original_tags}</div>
        <nav class="related" aria-label="相邻文章">{related}</nav>
        {comments}
      </div>
    </div>
  </article>'''
    head = (
        f'{cover}\n<meta name="giscus:backlink" content="{html(SITE + post.path)}">\n'
        '<script src="/js/comments.js" defer></script>'
    )
    return shell(post.title, post.path, content, post.description, head)


def listing(title, path, posts, pagination="", intro=""):
    return shell(title, path, f'<section class="listing"><h1>{html(title)}</h1>{intro}{post_rows(posts)}{pagination}</section>')


def path_for(file):
    relative = file.relative_to(ROOT).as_posix()
    return normalized_path("/" + relative.removesuffix("index.html"))


def write(path, content):
    target = ROOT / unquote(path).lstrip("/")
    if path.endswith("/"):
        target /= "index.html"
    if target.suffix == ".html":
        content = re.sub(r"(?m)^[ \t]+$", "", content)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_text() != content:
        target.write_text(content)


def pagination(path, total, current):
    if total <= 1:
        return ""
    numbers = sorted({1, total, *range(max(1, current - 2), min(total, current + 2) + 1)})
    items = []
    previous = 0
    for page in numbers:
        if previous and page - previous > 1:
            items.append('<span aria-hidden="true">…</span>')
        url = path if page == 1 else f"{path}page/{page}/"
        state = ' aria-current="page"' if page == current else ""
        items.append(f'<a href="{html(url)}"{state}>{page}</a>')
        previous = page
    return '<nav class="pagination" aria-label="文章分页">' + "".join(items) + "</nav>"


def taxonomy_groups(posts, attribute):
    groups = {}
    for post in posts:
        for name, url in getattr(post, attribute):
            if url not in groups:
                groups[url] = (name, [])
            groups[url][1].append(post)
    return groups


def taxonomy_listings(groups, historical=None):
    for url, (name, members) in groups.items():
        write(url, listing(name, url, members))
        for file in (ROOT / unquote(url).lstrip("/")).glob("page/*/index.html"):
            page = int(file.parent.name)
            path = path_for(file)
            paged_members = historical.get(url, (name, members))[1] if historical else members
            write(path, listing(name, path, paged_members[10 * (page - 1):10 * page],
                                intro=f'<p><a href="{html(url)}">查看此主题的全部文章</a></p>'))


def category_indexes(posts, catalog):
    old = taxonomy_groups(posts, "categories")
    taxonomy_listings(old)
    history = sorted(
        ((name, url, len(members)) for url, (name, members) in old.items()),
        key=lambda item: (-item[2], item[0]),
    )
    for node in catalog.walk():
        write(node.url, shell(node.name, node.url, browser_page(catalog, node, post_rows, history)))


def tag_indexes(posts):
    old = taxonomy_groups(posts, "tags")
    edited = taxonomy_groups(posts, "editorial_tags")
    taxonomy_listings({**old, **edited}, historical=old)
    current = sorted(edited.items(), key=lambda row: (-len(row[1][1]), row[1][0].casefold()))
    common, rest = [], []
    for url, (name, members) in current:
        item = f'<li><a href="{html(url)}">{html(name)} <span>{len(members)}</span></a></li>'
        (common if len(members) >= 2 else rest).append(item)
    more = ('<details class="catalog-history"><summary>更多标签</summary>'
            f'<ul class="taxonomy">{"".join(rest)}</ul></details>') if rest else ""
    body = ('<section class="listing tag-library" data-tag-library>'
            '<header class="page-heading"><h1>文章标签</h1><a href="/categories/">按分类浏览 ↗</a></header>'
            '<label class="tag-search" hidden>筛选标签<input type="search" data-tag-filter placeholder="例如 Python 或 MCP"></label>'
            '<p data-tag-status role="status"></p>'
            f'<ul class="taxonomy">{"".join(common)}</ul>{more}</section>')
    write("/tags/", shell("标签", "/tags/", body))


def archive(posts):
    by_year = defaultdict(list)
    for post in posts:
        by_year[post.day[:4]].append(post)
    entries = "".join(
        f'<section class="archive-year" id="y{year}"><h2><a href="/archives/{year}/">{year} 年</a>'
        f'<small>{len(members)} 篇</small></h2>{post_rows(members)}</section>'
        for year, members in by_year.items()
    )
    years = "".join(f'<a href="#y{year}">{year}<small>{len(members)} 篇</small></a>' for year, members in by_year.items())
    content = (f'<section class="listing archive"><header class="page-heading"><div><h1>文章归档</h1>'
               f'<p>{len(posts)} 篇文章</p></div><a href="/categories/">按分类浏览 ↗</a></header>'
               f'<nav class="archive-nav" aria-label="按年份浏览">{years}</nav>{entries}</section>')
    write("/archives/", shell("文章归档", "/archives/", content))
    for year, members in by_year.items():
        path = f"/archives/{year}/"
        write(path, listing(f"{year} 年文章", path, members))
    for file in (ROOT / "archives").glob("[0-9][0-9][0-9][0-9]/**/index.html"):
        segments = file.relative_to(ROOT / "archives").parts[:-1]
        year = segments[0]
        if len(segments) == 1:
            continue
        month = segments[1] if segments[1].isdigit() else ''
        match = year + (f"-{month}" if month else '')
        members = [post for post in by_year[year] if post.day.startswith(match)]
        if "page" in segments:
            start = 10 * (int(segments[-1]) - 1)
            members = members[start:start + 10]
        path = path_for(file)
        write(path, listing(f"{year} 年" + (f" {int(month)} 月" if month else "") + "文章", path, members))


def indexes(posts, catalog):
    count = (len(posts) + 9) // 10
    for base in ("/", "/archives/"):
        for page in range(2, count + 1):
            path = f"{base}page/{page}/"
            write(path, listing(f"全部文章 · 第 {page} 页", path, posts[(page - 1) * 10:page * 10], pagination(base, count, page)))
    for file in (ROOT / "archives/page").glob("*/index.html"):
        if file.parent.name == "1":
            write(path_for(file), listing("文章归档", path_for(file), posts[:10], pagination("/archives/", count, 1)))
    archive(posts)
    category_indexes(posts, catalog)
    tag_indexes(posts)
    search = [{"path": post.path, "title": post.title, "date": post.day,
               "text": post.search_text, "summary": unescape(excerpt(post.description, 180)), "topics": list(dict.fromkeys(
                   [topic.name for topic in post.topic.trail()] + [name for name, _ in post.editorial_tags or post.tags]
               ))} for post in posts]
    write("/search.json", json.dumps(search, ensure_ascii=False, separators=(",", ":")) + "\n")
    search_xml = ET.Element("search")
    for post in posts:
        entry = ET.SubElement(search_xml, "entry")
        for name, value in [("title", post.title), ("link", post.path.lstrip("/")), ("url", post.path.lstrip("/")), ("content", post.body)]:
            ET.SubElement(entry, name).text = value
        categories = [(topic.name, topic.url) for topic in post.topic.trail()]
        for collection, tag in [(categories, "category"), (post.editorial_tags or post.tags, "tag")]:
            if collection:
                parent = ET.SubElement(entry, f"{tag[:-1]}ies" if tag == "category" else "tags")
                for label, _ in collection:
                    ET.SubElement(parent, tag).text = label
    write("/search.xml", '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(search_xml, encoding="unicode"))
    atom_ns = "http://www.w3.org/2005/Atom"
    feed = ET.Element("feed", xmlns=atom_ns)
    ET.SubElement(feed, "title").text = NAME
    ET.SubElement(feed, "id").text = "http://zx490336534.github.io/"
    ET.SubElement(feed, "link", href=SITE + "/")
    ET.SubElement(feed, "link", href=SITE + "/atom.xml", rel="self")
    ET.SubElement(feed, "updated").text = timestamp(posts[0])
    ET.SubElement(ET.SubElement(feed, "author"), "name").text = "听白"
    for post in posts[:20]:
        entry = ET.SubElement(feed, "entry")
        ET.SubElement(entry, "id").text = ("http://zx490336534.github.io" if not post.path.startswith("/article/wechat-") else SITE) + post.path
        ET.SubElement(entry, "title").text = post.title
        ET.SubElement(entry, "link", href=SITE + post.path)
        ET.SubElement(entry, "updated").text = timestamp(post)
        ET.SubElement(entry, "published").text = timestamp(post)
        ET.SubElement(entry, "summary").text = post.description
        ET.SubElement(entry, "content", type="html").text = post.body
    write("/atom.xml", '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(feed, encoding="unicode"))


def timestamp(post):
    return post.published if "T" in post.published else post.published + "T00:00:00+08:00"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-posts", type=Path, help="已核验的公众号文章 JSON")
    args = parser.parse_args()
    posts = [read_post(path) for path in sorted((ROOT / "article").glob("*.html"))]
    assert posts and len({post.path for post in posts}) == len(posts)
    if args.import_posts:
        posts = import_posts(args.import_posts, posts)
    posts.sort(key=lambda post: (post.published, post.path), reverse=True)
    catalog = read_catalog(posts, ROOT / "scripts/topic_catalog.json")
    write("/", home(posts, catalog))
    for i, post in enumerate(posts):
        older = posts[i + 1] if i + 1 < len(posts) else None
        newer = posts[i - 1] if i else None
        write(post.path, article(post, older, newer))
    indexes(posts, catalog)
    lab = (
        '<section class="listing resource-library"><header class="page-heading">'
        '<div><h1>工具与课程</h1><p>打开在线工具，或按学习地图循序阅读。</p></div>'
        '</header>' + resource_cards() + '</section>'
    )
    write("/lab/", shell("工具与课程", "/lab/", lab))
    about = BeautifulSoup((ROOT / "about/index.html").read_text(), "lxml").select_one(".post-body")
    assert about is not None
    about_body = about.decode_contents().strip()
    if about.get_text(strip=True) == "施工中⚠️":
        about_body = (
            "<p>我是听白。在测试游记，我记录测试开发、自动化测试和 AI 工程的实战经验。</p>"
            "<p>可以按分类找一个主题，按年份回看文章，或从工具与课程开始上手。</p>"
        )
    profile = (
        '<section class="listing profile"><header class="page-heading"><div><h1>关于测试游记</h1><p>听白</p></div>'
        '<img class="profile-avatar" src="/images/avatar.jpeg" alt="" width="72" height="72"></header>'
        f'<div class="post-body">{about_body}</div>'
        '<nav class="profile-links" aria-label="继续浏览"><a href="/categories/">浏览分类 ↗</a>'
        '<a href="/lab/">工具与课程 ↗</a><a href="/atom.xml">订阅 RSS ↗</a></nav>'
        '<p class="analytics-notice">本站使用 Umami 统计公开页面访问和常用入口点击。统计字段为页面路径、标题、来源站点和入口。'
        '浏览器的不跟踪或全局隐私信号会关闭统计。</p></section>'
    )
    write("/about/", shell("关于", "/about/", profile))
    missing = ('<section class="listing missing-page"><header class="page-heading"><h1>找不到页面</h1></header>'
               '<div class="profile-links"><a href="/archives/">浏览文章归档 ↗</a><a href="/">返回首页 ↗</a>'
               '<button type="button" data-open-search>搜索文章</button></div></section>')
    write("/404.html", shell("找不到页面", "/404.html", missing))
    add_analytics_to_resources()
    print(f"已生成 {len(posts)} 篇文章及首页、归档、分类、搜索和 RSS。")


if __name__ == "__main__":
    main()
