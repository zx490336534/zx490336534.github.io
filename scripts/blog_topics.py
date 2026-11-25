"""The blog's editorial category tree and per-article tags."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote


@dataclass
class Topic:
    key: str
    name: str
    description: str
    parent: Topic | None = None
    children: list[Topic] = field(default_factory=list)
    members: list = field(default_factory=list)

    @property
    def url(self):
        return f"/categories/{self.key}/" if self.key else "/categories/"

    def trail(self):
        return [*self.parent.trail(), self] if self.parent else []

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def tag_key(name):
    return unicodedata.normalize("NFKC", name).casefold()


def read_catalog(posts, path):
    config = json.loads(path.read_text())
    root = Topic("", "文章分类", "")
    topics = {"": root}
    for key, (name, brief) in config["topics"].items():
        if not re.fullmatch(r"[a-z0-9-]+(?:/[a-z0-9-]+){0,2}", key):
            raise ValueError(f"无效分类路径 {key}")
        parent = topics[key.rpartition("/")[0]]
        node = Topic(key, name, brief, parent)
        topics[key] = node
        parent.children.append(node)

    legacy_urls = {tag_key(name): url for post in posts for name, url in post.tags}
    unassigned = None
    for post in posts:
        record = config["posts"].get(Path(post.path).stem)
        if record:
            topic_key, *names = record
            post.topic = topics[topic_key]
            for name in dict.fromkeys(names):
                slug = re.sub(r"[^\w.-]+", "-", unicodedata.normalize("NFKC", name)).strip(".-")
                url = legacy_urls.get(tag_key(name), f"/tags/{quote(slug, safe='')}/")
                post.editorial_tags.append((name, url))
        else:
            if unassigned is None:
                unassigned = Topic("unclassified", "待分类", "等待编辑归类的最新文章。", root)
                root.children.append(unassigned)
            post.topic = unassigned
        root.members.append(post)
        for node in post.topic.trail():
            node.members.append(post)
    return root


def links(labels):
    return "".join(f'<a href="{escape(url)}">{escape(name)}</a>' for name, url in labels)


def topic_trail(topic):
    return " <span aria-hidden=\"true\">/</span> ".join(
        f'<a href="{node.url}">{escape(node.name)}</a>' for node in topic.trail()
    )


def node_link(node, current, label=None, count=True):
    selected = ' aria-current="page"' if current is node else ''
    amount = f'<small>{len(node.members)}</small>' if count else ""
    return f'<a href="{node.url}"{selected}><span>{escape(label or node.name)}</span>{amount}</a>'


def menu_item(node, current, open_keys):
    if not node.children:
        return f"<li>{node_link(node, current)}</li>"
    state = " open" if node.key in open_keys else ""
    children = "".join(menu_item(child, current, open_keys) for child in node.children)
    return (
        f'<li><details{state}><summary><span>{escape(node.name)}</span>'
        f'<small>{len(node.members)}</small></summary><ul>'
        f'<li class="catalog-all">{node_link(node, current, "查看全部" + node.name, count=False)}</li>'
        f'{children}</ul></details></li>'
    )


def topic_cards(children):
    cards = []
    for node in children:
        descendants = "".join(
            f'<a href="{child.url}">{escape(child.name)}</a>' for child in node.children
        )
        items = f'<div class="catalog-card-links">{descendants}</div>' if descendants else ""
        cards.append(
            f'<section class="catalog-card"><h2>{node_link(node, None)}</h2>'
            f'<p>{escape(node.description)}</p>{items}</section>'
        )
    return '<div class="catalog-cards">' + "".join(cards) + "</div>" if cards else ""


def browser_page(root, current, post_rows, historical):
    is_root = current is root
    open_keys = {node.key for node in current.trail()}
    if is_root and root.children:
        open_keys.add(root.children[0].key)
    tree = "".join(menu_item(node, current, open_keys) for node in root.children)
    root_link = node_link(root, current, "全部分类")
    trail = (
        '<nav class="catalog-breadcrumb" aria-label="分类位置">'
        f'<a href="{root.url}">全部分类</a> <span aria-hidden="true">/</span> {topic_trail(current)}</nav>'
        if not is_root else ""
    )
    description = f'<p>{escape(current.description)}</p>' if current.description else ""
    count = f"{len(current.members)} 篇文章"
    if is_root:
        count += f" · {len(root.children)} 个主题"
    display = topic_cards(current.children)
    if not is_root:
        display += (
            '<section class="catalog-results"><h2>文章</h2>'
            f'{post_rows(current.members, show_category=bool(current.children))}</section>'
        )
    original = ""
    if is_root and historical:
        old_links = "".join(
            f'<li><a href="{escape(url)}">{escape(name)} <small>{amount}</small></a></li>'
            for name, url, amount in historical
        )
        original = f'<details class="catalog-history"><summary>原有专栏与来源</summary><ul>{old_links}</ul></details>'
    compact = ' data-compact="true"' if not is_root else ''
    return f'''
<section class="catalog">
  <header class="catalog-heading">
    {trail}
    <div class="catalog-heading-row">
      <div><h1>{escape(current.name)}</h1>
        <div class="catalog-count">{count}</div>
      </div>
      <a href="/tags/">按标签浏览 <span aria-hidden="true">↗</span></a>
    </div>
    {description}
  </header>
  <div class="catalog-layout">
    <aside class="catalog-sidebar">
      <details class="catalog-menu" open{compact}>
        <summary>分类目录</summary>
        <nav aria-label="文章分类目录"><ul><li>{root_link}</li>{tree}</ul></nav>
      </details>
    </aside>
    <div class="catalog-content">{display}{original}</div>
  </div>
</section>'''
