"""Public discovery of article provenance, tested media, and related material."""
from collections import defaultdict
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

from blog_discovery import WATCH, json_ld, watch_path



PROFILE_FOCUS = "AI 应用开发、Agent 评测与研发效能"
PROFILE_SUMMARY = "听白的公开作品：TypeScript 测试用例脑图工具、Promptfoo Agent 回归案例，以及 Temporal Agent 恢复设计。可直接查看源码、演示和验证依据。"
TOOL_REPO = "https://github.com/zx490336534/next-ai-test-cases"
CODEX_RELEASE = TOOL_REPO + "/releases/tag/v0.3.0"
CODEX_EVIDENCE_TEST = TOOL_REPO + "/blob/v0.3.0/tests/codex-plugin.test.ts#L55"
SELECTED_WORK = (
    ("ai-test-cases", "开源应用", "AI 测试用例脑图",
     "把需求变成可编辑的用例节点，支持对话式修改，再从当前脑图导出 CSV 或 XMind。",
     "用 Next.js 和 TypeScript 实现对话式增删改、脑图编辑与文件导出。两版均可导入文字 Skill；完整版还支持 MCP 读取已配置的文档。",
     "仓库公开了界面示例、运行说明和测试代码。编辑和导出不需要模型；AI 生成需要配置模型。",
     (("打开工具", "/tools/test-cases/"), ("查看 GitHub 源码", TOOL_REPO), ("查看测试代码", TOOL_REPO + "/tree/main/tests"))),
    ("agent-regression", "可复跑案例", "把 Agent 失败变成回归测试",
     "Agent 回复看似正确，任务状态却不对。案例把这类失败拆成可执行断言。",
     "先固定输入和预期状态，再用 Promptfoo 分别验证回放样本和当前 Agent，区分两类结果能证明什么。",
     "文章给出状态约定、样本和运行方法；视频页附文字稿，便于对照。",
     (("看复跑步骤", "/article/promptfoo-agent-regression.html"), ("看视频与文字稿", "/videos/watch/promptfoo-agent-regression/"),
      ("更多 Agent 评测", "/series/agent-development/#case-reads"))),
    ("agent-recovery", "架构案例", "让 Agent 任务中断后能恢复",
     "外部写入已经成功，完成回执却丢了。直接重试可能重复写入，不重试又可能丢结果。",
     "用 Temporal 的 Workflow、Activity 和业务幂等拆分恢复责任，说明何时可以重试，何时需要查回已有结果。",
     "公开文章给出故障时序和验收思路；这是设计案例，不是线上部署或性能报告。",
     (("看恢复设计", "/article/temporal-agent-recovery.html"), ("看原文里的视频", "/article/temporal-agent-recovery.html#article-video-title"))),
)


def home_work():
    links = "".join(f'<li><a href="/about/#{slug}"><strong>{escape(title)}</strong><span>{escape(kind)}</span></a></li>'
                    for slug, kind, title, *_ in SELECTED_WORK)
    return ('<section class="home-work" aria-labelledby="home-work-title">'
            '<header><h2 id="home-work-title">代表作品</h2><a href="/about/#selected-work">作品与验证方式 →</a></header>'
            f'<ul>{links}</ul></section>')


DEMO_PREFIX = "/videos/portfolio/ai-test-cases-demo-v3"
DEMO_PATHS = tuple(DEMO_PREFIX + suffix for suffix in (".mp4", ".webp", ".zh-CN.vtt"))


def work_demo(root):
    if not all((root / path.lstrip("/")).is_file() and (root / path.lstrip("/")).stat().st_size > 0
               for path in DEMO_PATHS):
        return ""
    src, poster, track = DEMO_PATHS
    sample = DEMO_PREFIX + "-sample.csv"
    sample_link = (f' · <a href="{sample}" download>下载演示导出的 CSV（3 条虚构用例）</a>'
                   if (root / sample.lstrip("/")).is_file() else "")
    return (
        '<figure class="work-demo" aria-labelledby="ai-test-cases-demo-caption">'
        '<figcaption id="ai-test-cases-demo-caption">完整版实录｜Skill、MCP、对话增删改与导出 · 虚构需求、本地模拟模型</figcaption>'
        f'<video controls playsinline preload="none" width="1440" height="900" poster="{poster}" '
        'aria-labelledby="ai-test-cases-demo-caption">'
        f'<source src="{src}" type="video/mp4">'
        f'<track kind="captions" src="{track}" srclang="zh-CN" label="简体中文">'
        '</video><p><strong>1:09｜对话增删改。</strong> 在同一个聊天框新增「重复提交」用例，把它从 P1 改为 P0 并补上预期结果，再删除另一条用例。'
        '<br><strong>2:49｜核对导出。</strong> CSV 和 XMind 都保留了新增和修改，删除项不再出现。</p>'
        f'<p><a href="{src}" download>下载 MP4</a>{sample_link}</p></figure>'
    )


def work_cards(root):
    cards = []
    demo = work_demo(root)
    for slug, kind, title, problem, method, proof, links in SELECTED_WORK:
        actions = "".join(f'<li><a href="{escape(url)}">{escape(label)} <span aria-hidden="true">↗</span></a></li>' for label, url in links)
        feature = demo if slug == "ai-test-cases" else ""
        body = (f'<p class="work-kind">{escape(kind)}</p><h3 id="{slug}-title">{escape(title)}</h3>'
                f'<p>{escape(problem)}</p><dl><dt>怎么做</dt><dd>{escape(method)}</dd>'
                f'<dt>怎么核对</dt><dd>{escape(proof)}</dd></dl><ul>{actions}</ul>')
        if slug == "ai-test-cases":
            body += ('<p><strong>本地 Codex 插件：</strong>从看板选中要测的用例，记录执行结果和依据。'
                     '之后即使用例被编辑，仍可查到当时执行的版本。'
                     f' <a href="{CODEX_RELEASE}">查看 GitHub 发布版 v0.3.0</a> · '
                     f'<a href="{CODEX_EVIDENCE_TEST}">看版本留存测试</a></p>')
        layout = ' work-card-featured' if feature else ''
        contents = f'<div class="work-card-copy">{body}</div>{feature}' if feature else body
        cards.append(f'<article class="work-card{layout}" id="{slug}" aria-labelledby="{slug}-title">'
                     f'{contents}</article>')
    return ('<section class="selected-work" id="selected-work" aria-labelledby="work-title"><h2 id="work-title">代表作品</h2>'
            '<p>从能直接打开的工具，到可按步骤复跑的评测，再到故障恢复的设计。</p>'
            '<div class="work-cards' + (' with-demo' if demo else "") + '">' + "".join(cards) + '</div></section>')


def profile_metadata(site):
    path = site + "/about/"
    return json_ld({"@type": "ProfilePage", "url": path, "inLanguage": "zh-CN",
                    "description": PROFILE_SUMMARY, "mainEntity": {"@type": "Person",
                    "@id": path + "#tingbai", "name": "听白", "url": path,
                    "sameAs": "https://github.com/zx490336534"}})

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
