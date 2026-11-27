"""Build editorial video collections without changing article media or watch pages."""
from collections import defaultdict
from dataclasses import dataclass
from html import escape as h
from pathlib import Path

from blog_discovery import WATCH, json_ld, watch_path
from blog_series import CATALOG_SECTIONS

HEAD = ('<link rel="stylesheet" href="/css/video-series.css?v=2">\n'
        '<script src="/js/video-series.js?v=2" defer></script>')


@dataclass
class Playlist:
    slug: str
    title: str
    description: str
    section: str
    groups: list
    is_series: bool = True
    featured: bool = False

    @property
    def episodes(self):
        return [episode for _, group in self.groups for episode in group]

    @property
    def path(self):
        return f"/videos/series/{self.slug}/"

    @property
    def anchor(self):
        return ("videos-" if self.is_series else "topic-videos-") + self.slug.removeprefix("topic-" if not self.is_series else "\0")

    @property
    def seconds(self):
        return sum(episode.video["duration"] for episode in self.episodes)


def published(post):
    video = post.video or {}
    return (video.get("voice") == "zh-CN-XiaoxiaoNeural"
            and video.get("poster") and video.get("captions"))


def make_playlists(posts, series, positions):
    playlists = []
    for item in series:
        groups = [(label, [post for post in group if published(post)]) for label, group in item.groups]
        useful = [(label, group) for label, group in groups if group]
        if useful:
            playlists.append(Playlist(item.slug, item.title, item.description, item.section, useful,
                                      featured=item.featured))
    supplemental = defaultdict(list)
    for post in posts:
        if published(post) and post.path not in positions:
            trail = post.topic.trail() if post.topic else []
            supplemental[(trail[0].key, trail[0].name) if trail else ("other", "其他文章")].append(post)
    for (key, name), entries in sorted(supplemental.items()):
        playlists.append(Playlist("topic-" + key, f"{name} · 主题选看", "同主题但未编入正式系列的讲解，按最近发布顺序排列。",
                                  "topics", [("全部视频", entries)], is_series=False))
    memberships = {}
    for playlist in playlists:
        for post in playlist.episodes:
            memberships.setdefault(post.path, playlist)
    assert set(memberships) == {post.path for post in posts if published(post)}, "视频遗漏"
    return playlists, memberships


def clock(seconds):
    minutes, rest = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{rest:02d}" if hours else f"{minutes}:{rest:02d}"


def total(seconds):
    hours, minutes = divmod((seconds + 30) // 60, 60)
    return (f"{hours} 小时" + (f" {minutes} 分钟" if minutes else "")) if hours else f"{max(minutes, 1)} 分钟"


def episode_url(playlist, post):
    return f"{playlist.path}?episode={Path(post.path).stem}"


def fallback(post):
    stem = Path(post.path).stem
    return watch_path(stem) if stem in WATCH else post.path + "#article-video-title"


def image(post, hero=False):
    src = post.display_cover or post.video["poster"]
    attrs = 'fetchpriority="high"' if hero else 'loading="lazy"'
    return f'<img src="{h(src)}" alt="" width="640" height="360" decoding="async" {attrs}>'


PLAY_ICON = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M8 5.6v12.8l10-6.4z" fill="currentColor"/></svg>'


def library(posts, playlists, memberships, site):
    series = [p for p in playlists if p.is_series]
    hero = next((p for p in series if p.slug == "agent-development"), None) or (series[0] if series else playlists[0])
    first = hero.episodes[0]
    description = "从测试自动化、Agent 评测和 AI 工程等系列开始，按集连续观看测试游记的中文视频。"
    data = json_ld({
        "@type": "CollectionPage", "name": "视频系列", "url": site + "/videos/",
        "description": description, "inLanguage": "zh-CN",
    })
    ordered_sections = [("ai", CATALOG_SECTIONS["ai"]), *((key, name) for key, name in CATALOG_SECTIONS.items() if key != "ai"),
                        ("topics", "更多主题选看")]
    sections = []
    nav = []
    for key, label in ordered_sections:
        items = [p for p in playlists if p.section == key]
        if not items:
            continue
        nav.append(f'<a href="#video-section-{key}">{h(label)}</a>')
        cards = []
        for item in items:
            cover = item.episodes[0]
            cards.append(f"""<article class="vc-card" id="{item.anchor}">
              <a href="{item.path}">
                <span class="vc-art">{image(cover)}<span class="vc-art-play">{PLAY_ICON}</span>
                <span class="vc-art-count">{len(item.episodes)} 集</span></span>
                <span class="vc-card-text"><strong>{h(item.title)}</strong><span>{h(item.description)}</span>
                <span class="vc-card-meta">{total(item.seconds)} <span aria-hidden="true">↗</span></span></span>
              </a></article>""")
        sections.append(f'<section class="vc-shelf" id="video-section-{key}" aria-labelledby="vc-section-title-{key}">'
                        f'<h2 id="vc-section-title-{key}">{h(label)}</h2>'
                        f'<div class="vc-grid">{"".join(cards)}</div></section>')
    rows = []
    other_memberships = defaultdict(list)
    for item in playlists:
        for post in item.episodes:
            other_memberships[post.path].append(item.title)
    for post in posts:
        if post.path not in memberships:
            continue
        item = memberships[post.path]
        tags = " ".join(other_memberships[post.path])
        sec = post.video["duration"]
        rows.append(f'<li data-episode-title="{h(post.title)}" data-episode-group="{h(tags)}">'
                    f'<div><a class="vc-index-play" href="{fallback(post)}" data-player-url="{episode_url(item, post)}">{h(post.title)}</a>'
                    f'<small>{h(item.title)}</small></div>'
                    f'<time datetime="PT{sec}S">{clock(sec)}</time></li>')
    transcripts = "".join(f'<li><a href="{fallback(post)}">{h(post.title)}</a></li>'
                          for post in posts if published(post) and Path(post.path).stem in WATCH)
    return f"""<section class="vc-library" data-video-library>
      <header class="vc-title"><h1>视频系列</h1></header>
      <section class="vc-hero" aria-label="推荐系列">
        <div class="vc-hero-copy"><p class="vc-eyebrow">推荐系列</p>
          <h2>{h(hero.title)}</h2><p>{h(hero.description)}</p>
          <div class="vc-hero-meta">{len(hero.episodes)} 集 <span>·</span> {total(hero.seconds)} <span>·</span> 简体中文字幕</div>
          <a class="vc-start" href="{hero.path}">{PLAY_ICON} 从第 1 集开始</a></div>
        <a class="vc-hero-art" href="{hero.path}" aria-label="打开{h(hero.title)}">
          {image(first, hero=True)}</a></section>
      <div class="vc-library-tools"><nav aria-label="视频主题">{"".join(nav)}</nav>
        <search class="vc-filter" aria-label="筛选视频" hidden><label class="visually-hidden" for="video-query">按片名或系列筛选视频</label>
        <div><input type="search" id="video-query" autocomplete="off" placeholder="搜索片名或系列"><button type="button" hidden>清空</button></div>
        <p role="status" aria-live="polite"></p></search></div>
      <div class="vc-shelves">{"".join(sections)}</div>
      <details class="vc-index"><summary>浏览全部视频</summary>
        <ul>{"".join(rows)}</ul></details>
      <section class="vc-standalone" aria-labelledby="vc-transcript"><h2 id="vc-transcript">带分章文字稿的独立视频</h2>
        <ul>{transcripts}</ul></section>
    </section>""", description, HEAD + data


def player(playlist, site):
    episodes = playlist.episodes
    first = episodes[0]
    title = first.title
    media = first.video
    first_transcript = f'href="{h(fallback(first))}"' if Path(first.path).stem in WATCH else "hidden"
    groups = []
    i = 0
    for label, members in playlist.groups:
        links = []
        for post in members:
            i += 1
            v = post.video
            links.append(f"""<li><a href="{fallback(post)}" data-player-episode="{Path(post.path).stem}" data-title="{h(post.title)}"
                  data-article="{h(post.path)}" data-src="{h(v["src"])}" data-poster="{h(v["poster"])}"
                  data-captions="{h(v["captions"])}" data-duration="{clock(v["duration"])}"
                  {' aria-current="true"' if i == 1 else ''}>
                  <span class="vp-number">{i:02d}</span><span class="vp-episode-name">{h(post.title)}</span>
                  <time datetime="PT{v["duration"]}S">{clock(v["duration"])}</time></a></li>""")
        groups.append(f'<h3>{h(label)}</h3><ol>{"".join(links)}</ol>')
    type_label = "按集连续观看" if playlist.is_series else "同主题视频选集"
    original = f'<a href="/series/{playlist.slug}/">系列图文目录 ↗</a>' if playlist.is_series else ""
    description = f"{playlist.title}，共 {len(episodes)} 集。{playlist.description}"
    data = json_ld({"@type": "CollectionPage", "name": playlist.title, "url": site + playlist.path,
                    "description": description, "inLanguage": "zh-CN"})
    return f"""<section class="vp" data-playlist aria-labelledby="vp-title">
      <nav class="vp-path" aria-label="位置"><a href="/videos/">← 视频系列</a><span>{type_label}</span></nav>
      <header class="vp-header"><p class="vc-eyebrow">{h(CATALOG_SECTIONS.get(playlist.section, '主题选看'))} · {len(episodes)} 集 · {total(playlist.seconds)}</p>
        <h1 id="vp-title">{h(playlist.title)}</h1><p>{h(playlist.description)}</p>{original}</header>
      <div class="vp-layout">
        <section class="vp-view" aria-labelledby="vp-now"><div class="vp-screen">
          <video controls playsinline preload="none" width="1280" height="720" poster="{h(media["poster"])}" aria-labelledby="vp-now">
            <source src="{h(media["src"])}" type="video/mp4">
            <track kind="captions" srclang="zh-CN" label="简体中文" src="{h(media["captions"])}">
          </video></div>
          <div class="vp-caption"><p class="vc-eyebrow" data-position>正在观看 · 第 1 / {len(episodes)} 集</p>
            <h2 id="vp-now">{h(title)}</h2>
            <div class="vp-source"><a href="{h(first.path)}" data-player-article target="_blank" rel="noopener">读图文原文 ↗</a>
            <a {first_transcript} data-player-transcript target="_blank" rel="noopener">分章文字稿 ↗</a></div></div>
          <div class="vp-controls" data-controls hidden><label><input type="checkbox" checked data-autonext> 自动连播</label>
            <div><button type="button" data-previous disabled>上一集</button><button type="button" data-next>下一集</button></div></div>
          <p class="vp-status"><span data-player-status role="status"></span><button type="button" data-retry hidden>点击播放</button></p>
        </section>
        <nav class="vp-queue" aria-label="选集"><div class="vp-queue-title"><h2>选集</h2><span>{len(episodes)} 集</span></div>
          <div class="vp-queue-scroll">{"".join(groups)}</div></nav>
      </div>
    </section>""", description, HEAD + data
