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
NAME = "测试游记"
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


def shell(title, path, content, description=DESCRIPTION, extra_head=""):
    title_tag = NAME if path == "/" else f"{title} · {NAME}"
    nav = [("文章归档", "/archives/"), ("分类", "/categories/"), ("教学", "/#courses"), ("关于", "/about/")]
    links = []
    for label, url in nav:
        current = ' aria-current="page"' if url == path else ""
        if not current and url == "/categories/" and path.startswith(url):
            current = ' aria-current="location"'
        links.append(f'<a href="{url}"{current}>{label}</a>')
    links = "".join(links)
    canonical = html(SITE + path)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{html(title_tag)}</title>
  <meta name="description" content="{html(description)}">
  <meta property="og:title" content="{html(title_tag)}">
  <meta property="og:description" content="{html(description)}">
  <meta property="og:url" content="{canonical}">
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" href="/atom.xml" type="application/atom+xml" title="测试游记">
  <link rel="icon" href="/images/avatar.jpeg">
  <link rel="stylesheet" href="/css/blog.css">
  <script src="/js/blog.js" defer></script>
  {extra_head}
</head>
<body>
  <a class="skip-link" href="#main">跳到正文</a>
  <header class="masthead">
    <div class="wrap masthead-inner">
      <a class="wordmark" href="/">测试游记<span>听白</span></a>
      <nav aria-label="主导航">{links}</nav>
      <button type="button" data-open-search class="search-trigger">搜索 <kbd>⌘/Ctrl K</kbd></button>
    </div>
  </header>
  <main id="main" class="wrap">{content}</main>
  <footer class="wrap footer">
    <a class="footer-brand" href="/">测试游记</a>
    <a href="/archives/">文章归档</a><a href="/tags/">标签</a><a href="/atom.xml">RSS</a>
  </footer>
  <dialog id="search-dialog" aria-labelledby="search-title">
    <div class="search-heading"><h2 id="search-title">搜索文章</h2><form method="dialog"><button>关闭</button></form></div>
    <label class="visually-hidden" for="article-search">搜索文章标题和正文</label>
    <input id="article-search" type="search" placeholder="搜索标题或正文…" autocomplete="off" autofocus>
    <p id="search-status" role="status"></p><ol id="search-results"></ol>
  </dialog>
</body>
</html>
'''


def date_label(post):
    return f'<time datetime="{html(post.published)}">{html(post.day)}</time>'


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


def home_story(post, picture, layout):
    lead = layout == "front-lead"
    heading = "h3" if layout == "front-card" else "h2"
    priority = 'fetchpriority="high"' if lead else 'loading="lazy"'
    image = (f'<div class="front-media"><img src="{html(picture)}" alt="" '
             f'decoding="async" {priority}></div>') if picture else ""
    status = '<span class="front-kicker">最新发布</span>' if lead else ""
    action = '<span class="front-read">阅读全文 <span aria-hidden="true">↗</span></span>' if lead else ""
    return f'''<article class="{layout}">
      <a href="{html(post.path)}" class="front-story">
        {image}
        <div class="front-copy">
          <div class="front-meta">{status}{date_label(post)}</div>
          <{heading}>{html(post.title)}</{heading}>
          <p>{excerpt(post.description, 150)}</p>
          {action}
        </div>
      </a>
    </article>'''


def home(posts):
    feature = posts[0]
    photos = []
    for post in posts[1:40]:
        picture = home_picture(post)
        if picture:
            photos.append((post, picture))
        if len(photos) == 8:
            break

    aside = "".join(home_story(post, picture, "front-related") for post, picture in photos[:2])
    rail = f'<div class="front-rail">{aside}</div>' if aside else ""
    gallery = "".join(home_story(post, picture, "front-card") for post, picture in photos[2:])
    illustrated = f'''
  <section class="section" aria-labelledby="illustrated-title">
    <header class="section-title"><h2 id="illustrated-title">图文选读</h2></header>
    <div class="front-gallery">{gallery}</div>
  </section>''' if gallery else ""
    featured = {post.path for post, _ in photos}
    recent = [post for post in posts[1:] if post.path not in featured][:7]
    content = f'''
  <header class="front-heading">
    <h1>测试开发与 AI 工程实践</h1>
    <a href="/archives/">浏览归档 <span aria-hidden="true">↗</span></a>
  </header>
  <section class="front-grid {'with-rail' if rail else ''}" aria-label="精选文章">
    {home_story(feature, home_picture(feature), "front-lead")}
    {rail}
  </section>
  <section class="front-tool" aria-labelledby="tools-title">
    <h2 id="tools-title">在线工具</h2>
    <a href="{SITE}/tools/test-cases/">测试用例脑图生成器 <span aria-hidden="true">↗</span></a>
  </section>
  {illustrated}
  <section class="section" aria-labelledby="recent-title">
    <header class="section-title"><h2 id="recent-title">近期文章</h2><a href="/archives/">全部文章 <span aria-hidden="true">→</span></a></header>
    {post_rows(recent)}
  </section>
  <section class="section" id="courses" aria-labelledby="courses-title">
    <header class="section-title"><h2 id="courses-title">教学专题</h2></header>
    <div class="course-grid">
      <a href="/teaching-aihom/lessons/index.html"><strong>AIHom 完整学习地图</strong><span aria-hidden="true">↗</span></a>
      <a href="/teaching-kuai/lessons/index.html"><strong>Kuai 测试平台学习地图</strong><span aria-hidden="true">↗</span></a>
    </div>
  </section>'''
    return shell(NAME, "/", content)


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
    comments = f'<section class="comments" id="comments" hidden><div id="disqus_thread" data-identifier="{html(post.path.lstrip("/"))}"></div></section>' if post.legacy_comments else ''
    cover = f'<meta name="blog-cover" content="{html(post.cover)}"><meta property="og:image" content="{html(SITE + post.cover)}">' if post.cover else ''
    content = f'''
  <article class="article">
    <header class="article-header">
      <a class="back-link" href="/archives/">← 文章归档</a>
      <h1 class="post-title">{html(post.title)}</h1>
      <div class="entry-meta"><span class="post-author">{html(post.author)}</span><time itemprop="datePublished" datetime="{html(post.published)}">{html(post.day)}</time>
        <span class="post-category" hidden>{original_categories}</span>
        <nav class="topic-context" aria-label="文章分类">{trail}</nav></div>
    </header>
    <div class="article-layout {'with-outline' if outline else ''}">
      {outline}
      <div class="article-main">
        <div class="post-body">{post.body}</div>
        {source}
        <div class="post-tags">{tags}</div>
        <div class="legacy-tags" hidden>{original_tags}</div>
        <nav class="related" aria-label="相邻文章">{related}</nav>
        {comments}
      </div>
    </div>
  </article>'''
    return shell(post.title, post.path, content, post.description, cover)


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


def pagination(path, total):
    if total <= 1:
        return ""
    return '<nav class="pagination" aria-label="文章分页">' + "".join(
        f'<a href="{html(path if page == 1 else f"{path}page/{page}/")}">{page}</a>'
        for page in range(1, total + 1)
    ) + '</nav>'


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
    body = ('<section class="listing tag-library"><header class="section-title"><h1>标签</h1>'
            '<a href="/categories/">按分类浏览 ↗</a></header>'
            f'<ul class="taxonomy">{"".join(common)}</ul>{more}</section>')
    write("/tags/", shell("标签", "/tags/", body))


def archive(posts):
    by_year = defaultdict(list)
    for post in posts:
        by_year[post.day[:4]].append(post)
    entries = "".join(f'<section class="archive-year" id="y{year}"><h2><a href="/archives/{year}/">{year}</a></h2>{post_rows(members)}</section>'
                      for year, members in by_year.items())
    years = "".join(f'<a href="#y{year}">{year}</a>' for year in by_year)
    write("/archives/", shell("文章归档", "/archives/", f'<section class="listing"><h1>文章归档</h1><p>{len(posts)} 篇文章</p><nav class="pagination" aria-label="按年份浏览">{years}</nav>{entries}</section>'))
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
            write(path, listing(f"全部文章 · 第 {page} 页", path, posts[(page - 1) * 10:page * 10], pagination(base, count)))
    for file in (ROOT / "archives/page").glob("*/index.html"):
        if file.parent.name == "1":
            write(path_for(file), listing("文章归档", path_for(file), posts[:10], pagination("/archives/", count)))
    archive(posts)
    category_indexes(posts, catalog)
    tag_indexes(posts)
    search = [{"path": post.path, "title": post.title, "date": post.day,
               "text": post.search_text, "topics": list(dict.fromkeys(
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
    write("/", home(posts))
    for i, post in enumerate(posts):
        older = posts[i + 1] if i + 1 < len(posts) else None
        newer = posts[i - 1] if i else None
        write(post.path, article(post, older, newer))
    indexes(posts, catalog)
    about = BeautifulSoup((ROOT / "about/index.html").read_text(), "lxml").select_one(".post-body")
    assert about is not None
    write("/about/", shell("关于", "/about/", f'<section class="listing"><h1>关于</h1><div class="post-body">{about.decode_contents().strip()}</div></section>'))
    write("/404.html", shell("找不到页面", "/404.html", '<section class="listing"><h1>找不到页面</h1><p><a href="/archives/">浏览文章归档</a> · <a href="/">返回首页</a></p></section>'))
    print(f"已生成 {len(posts)} 篇文章及首页、归档、分类、搜索和 RSS。")


if __name__ == "__main__":
    main()
