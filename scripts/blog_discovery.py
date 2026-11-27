"""Search discovery and editorial evidence for public blog routes."""
from datetime import datetime
from html import escape, unescape
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

HOME_TITLE = "测试游记｜AI Agent 评测、测试开发与自动化实践"
HOME_SUMMARY = "听白的技术博客。用可复现案例讲解 AI Agent 评测、测试开发和自动化实践，提供实战文章、系列教程及测试用例脑图工具。"
TOOL_PATH = "/tools/test-cases/"
TOOL_TITLE = "AI 测试用例生成器与脑图编辑器 · 测试游记"
TOOL_SUMMARY = "把产品需求整理成测试点和测试用例，用脑图查看、编辑和导出。单文件版支持离线编辑及导出；AI 生成功能需要兼容的模型网关。"

# A short decision aid alongside the original article, never inside .post-body.
EVIDENCE = {
    "promptfoo-agent-regression": (
        "Agent 状态回归该断言什么？", "断言排队状态与产物字段的约束，不能只检查回复里有没有「排队」。",
        "被测应用有可重复准备的排队状态，且响应结构是明确的业务契约。",
        "固定的四条样本里，一条通过、三条反例失败、零运行错误；换成本地模拟接口后，同一断言又区分出一条通过与一条失败。前者检验断言，后者还检验调用路径，两者都不是线上模型表现。",
    ),
    "llm-judge-empty-output": (
        "评测报告里，空输出要不要单列？", "把终态无产物、有产物时的质量判断和同题候选排序分开统计。",
        "模型裁判被用来辅助发布门禁或候选排序，且样本中同时有明确空输出与有效产物。",
        "构造例中，四条有产物样本只有两条与人工一致；加入四条双方都判失败的空输出，总体变为 6/8（75%），有产物组仍为 2/4（50%）。另一组构造数据中，汇总相关约 0.92，同题选对却为 0/3。",
    ),
    "agent-ui-testing": (
        "UI 提示保存成功，可以作为测试通过条件吗？", "把模型定位或操作与业务断言分开，以落地数据回读作为保存的结果证据。",
        "可以稳定回读本次产物；若保存异步，需先确认任务终态，再按当次标识回读，避免缓存或同名数据误判。",
        "原文对照两个本地模拟版本：两者都返回 HTTP 200、都提示保存成功，但刷新后只有写入版能找到卡片。仅验状态码或提示，会漏掉跳过写入的故障。",
    ),
    "temporal-agent-recovery": (
        "流程恢复后，怎么确认下游没有重复写入？", "分开验证流程能继续和下游写入幂等，不能从恢复成功推导出只写一次。",
        "保存 Activity 可能重试，且同一次业务操作能复用稳定的操作键。",
        "本地注入保存之后报错：假模型被调用一次，保存步骤两次，SQLite 最终一条产物记录；完成历史的重放没有再执行 Activity。这不是对真实进程退出或超时接管的验证。",
    ),
    "kitaru-agent-replay-regression": (
        "最后一句说已转人工，能证明 Agent 没尝试退款吗？", "用完整工具事件校验「没有尝试退款」且「成功升级人工」，不只看最后一句回复。",
        "对照使用同一批脱敏或构造样本、同一条断言与离线工具记录；命不中记录时记为不可比较。",
        "构造反例中，『只转人工』通过，『退款尝试失败后再转人工』与『什么也没做』均失败。单独保留正常可直接退款样本，以免全部转人工也过关。",
    ),
}

# Dates are the exact created_at values of the named public GitHub Release assets,
# not the post's publication date, release tag date, or site rebuild time.
WATCH = {
    "promptfoo-agent-regression": (
        "2026-11-25T08:37:53Z", "用 Promptfoo 验证排队状态：固定反例、本地模拟接口和发布回归的区别。",
        ((0, "排队状态与产物字段"), (25, "用固定反例检验断言"), (52, "切换到本地模拟接口"), (79, "区分环境错误与产品问题"), (106, "把回归接进发布门禁")),
    ),
    "llm-judge-empty-output": (
        "2026-11-25T08:37:34Z", "用构造样本说明空输出为何抬高总体一致率，以及如何改用分组质量与同题排序。",
        ((0, "总体一致率怎么变成 75%"), (25, "增加空输出的影响"), (51, "高相关但同题全选反"), (77, "按上线任务设计评测"), (102, "分别报告三个分母")),
    ),
    "agent-ui-testing": (
        "2026-11-25T08:42:21Z", "同样返回 200 和保存成功，为什么刷新后只有一个版本还读得到卡片？",
        ((0, "本地保存对照实验"), (28, "核对写入请求并回读"), (55, "缓存、异步与终态"), (85, "何时让视觉模型做定位"), (114, "用反例校验测试本身")),
    ),
}


def json_ld(*objects):
    markup = {"@context": "https://schema.org", "@graph": list(objects)}
    # Escape HTML script delimiters while keeping the JSON values identical.
    return '<script type="application/ld+json">' + json.dumps(markup, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c") + "</script>"


def watch_path(slug):
    return f"/videos/watch/{slug}/"


def article_metadata(post, site):
    article = {
        "@type": "BlogPosting",
        "headline": post.display_title,
        "description": post.description,
        "inLanguage": "zh-CN",
        "url": site + post.path,
        "mainEntityOfPage": {"@type": "WebPage", "@id": site + post.path},
        "author": {"@type": "Person", "name": post.author},
    }
    if post.published:
        try:
            datetime.fromisoformat(post.published)
        except ValueError:
            pass
        else:
            article["datePublished"] = post.published
    if post.author == "听白":
        article["author"]["url"] = site + "/about/"
    if post.display_cover:
        article["image"] = site + post.display_cover
    crumbs = [("分类", "/categories/")]
    if post.topic:
        sections = post.topic.trail()
        article["articleSection"] = [t.name for t in sections]
        crumbs += [(t.name, t.url) for t in sections]
    crumbs.append((post.display_title, post.path))
    breadcrumb = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": label, "item": site + path}
            for i, (label, path) in enumerate(crumbs, 1)
        ],
    }
    return json_ld(article, breadcrumb)


def home_intro():
    return f"""<section class="publication-intro" aria-labelledby="publication-title">
      <h1 id="publication-title">AI Agent 评测与测试开发实践</h1>
      <p>我是听白，关注 AI 应用开发、Agent 评测与研发效能。这里有开源工具、可复跑案例和工程设计笔记。</p>
      <div class="intro-links"><a href="/series/agent-development/">Agent 开发与评测专题 →</a><a href="/about/">关于听白</a></div>
    </section>"""


def series_evidence():
    links = "".join(f'<li><a href="/article/{slug}.html">{escape(record[0])}</a></li>' for slug, record in EVIDENCE.items())
    return ('<section class="editorial-evidence" aria-labelledby="case-reads"><h2 id="case-reads">从五个可验证的案例开始</h2>'
            f'<ul>{links}</ul><p><a href="{TOOL_PATH}">打开测试用例生成器与脑图编辑器 →</a> · <a href="/about/#selected-work">查看代表作品和验证方式 →</a></p></section>')


def evidence_card(post):
    slug = Path(post.path).stem
    if not (item := EVIDENCE.get(slug)):
        return ""
    title, conclusion, scope, proof = map(escape, item)
    return (f'<aside class="editorial-evidence" aria-labelledby="evidence-title"><h2 id="evidence-title">{title}</h2>'
            f'<dl><dt>结论</dt><dd>{conclusion}</dd><dt>适用条件</dt><dd>{scope}</dd>'
            f'<dt>可复核的证据</dt><dd>{proof}</dd></dl>'
            '<p><a href="/series/agent-development/#case-reads">继续看 Agent 评测案例 →</a></p></aside>')


def tool_metadata(site):
    url = site + TOOL_PATH
    return (f'<title>{TOOL_TITLE}</title>\n  <meta name="description" content="{TOOL_SUMMARY}">\n'
            f'  <link rel="canonical" href="{url}">\n  <meta property="og:title" content="{TOOL_TITLE}">\n'
            f'  <meta property="og:description" content="{TOOL_SUMMARY}">\n  <meta property="og:url" content="{url}">')


def tool_intro():
    return ('<details class="tool-guide"><summary>AI 测试用例生成器 · 使用说明</summary>'
            '<h1>AI 测试用例生成器与脑图编辑器</h1>'
            f'<p>{TOOL_SUMMARY}</p>'
            '<p><a href="/article/wechat-f7a449cd36e9a5.html">查看用例脑图实践 →</a></p></details>')


def caption_cues(path):
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip())
    if not blocks[0].startswith("WEBVTT"):
        raise ValueError(f"无效字幕：{path}")
    cues = []
    for block in blocks[1:]:
        lines = block.splitlines()
        if lines[0].split(maxsplit=1)[0] in {"NOTE", "STYLE", "REGION"}:
            continue
        timing = 0 if " --> " in lines[0] else 1  # A cue may begin with an identifier.
        if timing >= len(lines) or " --> " not in lines[timing]:
            raise ValueError(f"字幕缺少时间段：{path}")
        stamp = lines[timing].split(" --> ", 1)[0]
        seconds = 0
        for part in stamp.split(":"):
            seconds = seconds * 60 + float(part)
        text = " ".join(lines[timing + 1:]).strip()
        if text:
            markup = r"</?(?:[biu]|c|v|lang|ruby|rt)(?:[.\s][^>]*)?>|<(?:\d+:)?\d{2}:\d{2}\.\d{3}>"
            cues.append((seconds, unescape(re.sub(markup, "", text))))
    if not cues:
        raise ValueError(f"字幕缺少正文：{path}")
    return cues


def video_watch(post, root, site):
    slug = Path(post.path).stem
    published, description, chapters = WATCH[slug]
    media = post.video
    if not media or media.get("voice") != "zh-CN-XiaoxiaoNeural":
        raise ValueError(f"观看页缺少已发布的晓晓版：{post.path}")
    prefix = f"https://github.com/zx490336534/zx490336534.github.io/releases/download/article-videos-20261125/{slug}-xiaoxiao.mp4"
    if media["src"] != prefix:
        raise ValueError(f"观看页的上传时间只适用于已核对的 Release 资产：{post.path}")
    path = watch_path(slug)
    transcript = [[] for _ in chapters]
    for offset, text in caption_cues(root / media["captions"].lstrip("/")):
        part = max(i for i, (base, _) in enumerate(chapters) if offset >= base)
        transcript[part].append(text)
    if any(not part for part in transcript):
        raise ValueError(f"字幕与观看页章节不匹配：{post.path}")
    nav, sections, clips = [], [], []
    for i, ((seconds, label), lines) in enumerate(zip(chapters, transcript), 1):
        time = f"{seconds//60}:{seconds%60:02}"
        nav.append(f'<li><a href="?t={seconds}" data-watch-offset="{seconds}">{time} {escape(label)}</a> '
                   f'<a href="#chapter-{i}" aria-label="阅读{escape(label)}的文字稿">文字稿</a></li>')
        end = chapters[i][0] if i < len(chapters) else media["duration"]
        if not seconds < end <= media["duration"]:
            raise ValueError(f"观看页章节时间范围非法：{post.path} {seconds}–{end}")
        clips.append({"@type": "Clip", "name": label, "startOffset": seconds,
                      "endOffset": end, "url": f"{site}{path}?t={seconds}"})
        paragraphs = "".join(f"<p>{escape(line)}</p>" for line in lines)
        sections.append(f'<section id="chapter-{i}"><h3>{time} {escape(label)}</h3>{paragraphs}</section>')
    video = {
        "@type": "VideoObject",
        "name": post.display_title + "｜视频讲解",
        "description": description,
        "thumbnailUrl": [site + media["poster"]],
        "uploadDate": published,
        "duration": f'PT{media["duration"]}S',
        "contentUrl": media["src"],
        "inLanguage": "zh-CN",
        "url": site + path,
        "hasPart": clips,
    }
    body = f"""<article class="watch-page">
      <header><p class="article-path"><a href="/videos/">视频讲解目录</a></p><h1>{escape(post.display_title)}：视频讲解</h1></header>
      <video controls playsinline preload="metadata" width="1280" height="720" poster="{escape(media["poster"])}"
         aria-label="{escape(post.display_title)}">
        <source src="{escape(media["src"])}" type="video/mp4">
        <track kind="captions" srclang="zh-CN" label="简体中文" src="{escape(media["captions"])}">
      </video>
      <p>{escape(description)} <a href="{post.path}">查看图文原文 →</a> · <a href="{escape(media["src"])}">下载视频</a></p>
      <nav aria-label="视频章节"><h2>视频章节</h2><ol>{''.join(nav)}</ol></nav>
      <div class="watch-transcript" aria-labelledby="transcript-title"><h2 id="transcript-title">文字稿</h2>
        {''.join(sections)}
      </div>
    </article>"""
    head = (f'<meta property="og:type" content="video.other">\n'
            f'<meta property="og:image" content="{site}{escape(media["poster"])}">\n'
            '<script src="/js/video-chapters.js" defer></script>\n' + json_ld(video))
    return path, body, description, head


def sitemap(posts, series, site):
    paths = {
        "/", "/archives/", "/series/", "/categories/", "/about/", "/lab/", "/videos/", TOOL_PATH, "/tools/spec-collab/",
        *(p.path for p in posts), *(s.url for s in series), *(watch_path(slug) for slug in WATCH),
    }
    video_ns = "http://www.google.com/schemas/sitemap-video/1.1"
    ET.register_namespace("video", video_ns)
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    watch_entries = {watch_path(Path(p.path).stem): p for p in posts if Path(p.path).stem in WATCH}
    # Do not substitute deploy timestamps for editorial lastmod.
    for path in sorted(paths):
        url = ET.SubElement(root, "url")
        ET.SubElement(url, "loc").text = site + path
        if post := watch_entries.get(path):
            media = post.video
            published, description, _ = WATCH[Path(post.path).stem]
            node = ET.SubElement(url, f"{{{video_ns}}}video")
            for key, value in [
                ("thumbnail_loc", site + media["poster"]), ("title", post.display_title + "｜视频讲解"),
                ("description", description), ("content_loc", media["src"]),
                ("duration", str(media["duration"])), ("publication_date", published),
            ]:
                ET.SubElement(node, f"{{{video_ns}}}{key}").text = value
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
