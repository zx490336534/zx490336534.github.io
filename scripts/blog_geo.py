"""Article reading leads extracted from public prose and linked to the original."""
from html import escape
from pathlib import Path
import re
from urllib.parse import quote

from bs4 import BeautifulSoup


# In these topics a duplicated sentence or deep link could lift unsafe instructions out of context.
SENSITIVE_TOPIC = re.compile(
    r"爬取|新浪微博登[陆录]|漏洞|渗透|入侵|抓包|证书固定|中间人|报文拦截|破解|绕过|脱库|撞库|逆向|"
    r"攻击载荷|提权|木马|零日|后门|恶意代码|漏洞利用|钓鱼|"
    r"生物武器|病毒改造|基因编辑|病原体|炸弹|爆炸物|"
    r"mitmproxy|FLAG_SECURE|HttpCanary|Debookee|spy-debugger|Burp Suite|sqlmap|CVE-\d|exploit|payload injection", re.I)
HARD_RISK = re.compile(r"证书固定绕过|绕过验证|钓鱼页|截获凭据|反弹shell|漏洞利用|攻击载荷|"
                       r"远程代码执行漏洞|生物武器|病原体工程|病毒改造|exploit payload|sqlmap|meterpreter", re.I)
SENSITIVE_LINE = re.compile(
    r"https?://|www\.|(?<![.\w])(?:\d{1,3}\.){3}\d{1,3}(?![.\w])|[\w.+-]+@[\w.-]+\.[a-z]{2,}|"
    r"\b(?:sk|ghp|github_pat|xox[baprs]|AKIA|BEGIN PRIVATE KEY)[-_A-Za-z0-9]{12,}\b|"
    r"\b(?:cookie|authorization|password|secret|token|apikey|access key)\b|密钥|令牌|密码|"
    r"(?:[0-9]{7,}|1[3-9]\d{9}|[a-z0-9]{18,})|(?:[A-Z]:\\|/(?:Users|home|root)/)|"
    r"(?<!\w)(?:sudo|curl|export|wget|chmod|node|java)\s+(?=[-+/])|"
    r"(?:@[A-Za-z0-9_-]{2,}|\b(?:\w+\.)+(?:corp|internal|intranet|lan|local)\b)|"
    r"账号|帐号|账户|用户名|客户姓名|姓名|身份证|护照|手机号|登录名|凭证|Webhook|员工号|私信|微信|公众号|QQ号|群号|手机号|联系我|帮我|提示词如下|回复关键词|版权所有", re.I)
STALE_CLAIM = re.compile(r"目前|最新|唯一|最(?:流行|主流|强大)|所有版本|截至|已经停|仅支持|[0-9]+万元|收入|年薪|新赛道")
PRIVATE_OR_SENSITIVE_SECTION = re.compile(r"远程连接权限|内网连接|同一网络.*设备|执行操作|代码执行器|客户端身份|接口文档")
DISQUALIFY = re.compile(r"^(?:前言|引言|摘要|概述|介绍|背景|目录|效果|步骤|使用|其他|定义|示例|结果|思考|参考|参考资料|参考链接|参考文献|参考文档|相关资料|扩展阅读|广告|代码|视频|结尾|记录|写在最后|问题现象|开始使用|环境准备|环境搭建|新方案|原方案|具体编码|完整代码|代码编写|简单示例|一个简单的例子|先来看看效果|开始测试|查看结果|结果查看|运行结果|查看效果|最终效果|结果展示|效果演示|创建项目|搭建项目|基本语法|结束测试)$", re.I)
REFERENCE = re.compile(r"^(?:\d+[ .、：:]+\s*)?(?:参考(?:资料|链接|文献|文档)?|相关资料|扩展阅读|References)$", re.I)
WRAP_END = re.compile(r"^(?:(?:\d+[ .、：:]+|[一二三四五六七八九十]+[、：:])\s*)?(?:小结|总结|结论|经验总结|最后|要点|注意事项|使用建议|选型建议)$")
OUTCOME = re.compile(r"区别|不要|不适合|而不是|更适合|取决于|意味着|仍然|前提|只要|不能|应该|推荐|"
                     r"必须|用于|可以用|需要先|观察到|说明|发现|证据|原因|结果|实现了|分为|主要是")
SECTION_PRIORITY = re.compile(r"对照|对比|验证|测试|实战|示例|样例|结果|复盘|判断|改造|选择|适用|总结|结论|案例|核对|效果|局限")
SENTENCES = re.compile(r"(?<=[。！？])\s*")
HEADING = re.compile(r"^h[1-6]$")


# Read and written against the named public posts, in addition to the five existing long-form cards.
# Distinct from a test claim: what can be checked is a link to the author's own published demonstration.
NOTES = {
    "codex-obsidian-wiki": (
        "先保留原始笔记，再用 Codex 更新 Wiki 的主题结论；新证据出现时修订原条目，而不是继续堆一份同主题总结。",
        "适用于内容会持续演进、而且之后需要回查来路的个人知识库。任务调度的成功状态不能代替对写入结果的检查。",
        ("新证据来了，先改原来的结论", "新会话从索引开始读", "调度显示成功，先打开文件复核"),
    ),
    "pi-agent-four-tools": (
        "用一次失败单测判断四个默认工具够不够：先读取、再改动、再执行验证；新增扩展应能解决任务中观察到的缺口。",
        "这是编码助手与其本地工作区的例子。切换会话分支后，需要另查实际文件状态，不能把会话分支当成文件快照。",
        ("把失败单测交给四个工具", "一次调用从模型走到扩展，再返回给模型", "切换会话以后，先看工作区"),
    ),
    "mcp-gateway-name-collision": (
        "当两个 MCP 服务暴露同名工具，网关应能从唯一公开名找到目标后端；不论列表是否过滤，调用时都要再判断权限。",
        "讨论多服务聚合，不是某个后端鉴权协议的替代方案。上游在区分失败类别时应保留具体后端来源。",
        ("工具公开名要能直接查到后端", "列表可以精简，调用时还要检查权限", "接真服务，失败来源要保留下来"),
    ),
    "text-fragment-report-links": (
        "用 URL 文本片段把读者带到报告里的一段文字。重复内容要缩小匹配范围，不能只给一个到处出现的函数名。",
        "用于能公开分享的网页内容；要保留普通锚点或其他可手工找到的位置，避免某些客户端不跳转。",
        ("先从一段能唯一匹配的文字开始", "同一个函数名出现两次怎么办", "在这篇里试一下", "链接仍然要让人手动找得到"),
    ),
    "ai-visual-assertions-ui-testing": (
        "视觉模型只判断一个可观察的现象。用正常暗色图和被遮挡图一起验，不能把界面颜色当成是否失败的依据。",
        "适合没有稳定 DOM 或像素阈值的视觉检查；保存结果等业务状态仍应直接回读，不交给模型猜。",
        ("把要判断的现象说窄一点", "让脚本读到判断，还能查它的依据", "先把正常图和异常图一起跑一遍"),
    ),
    "traffic-replay-diff-report": (
        "HTTP 状态相同不代表回放一致；一条记录要能定位到不同的字段，并读出基线与候选各是什么。",
        "适用于获授权、可脱敏的回归样本。报告工具根据是看一次运行、看当天明细，还是跨天查询来选。",
        ("先让一条差异能看懂", "三种报告各自适合什么情况"),
    ),
}


def compact(text):
    return " ".join(text.split())


def safe(text, lo, hi, min_han=3):
    return (lo <= len(text) <= hi and not SENSITIVE_TOPIC.search(text) and not SENSITIVE_LINE.search(text)
            and len(re.findall(r"[\u3400-\u9fff]", text)) >= max(min_han, len(text) // 6)
            and not re.search(r'[<>{}=*\\]|\[[^\]]{1,80}\]', text))


def fragments(body):
    """Collect real h2/h3/h4 anchors with local prose, not snippets of executable code."""
    groups = [("article-text", "", "intro", [])]
    active = groups[0]
    for element in body.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        if element.find_parent(["pre", "code", "table", "blockquote", "figure"]):
            continue
        if HEADING.match(element.name):
            active = None
            if ((anchor := element.get("id")) and not SENSITIVE_LINE.search(anchor)
                    and not HARD_RISK.search(anchor)):
                active = (anchor, compact(element.get_text(" ", strip=True)), element.name, [])
                groups.append(active)
            continue
        if element.name == "li" and element.find("p"):
            continue
        if element.find(["a", "code", "img", "pre", "li"]):
            continue
        prose = compact(element.get_text(" ", strip=True))
        if active is not None and prose:
            active[3].append(prose)
    return groups


def source_excerpt(groups, title):
    candidates = []
    for i, (anchor, label, _, paragraphs) in enumerate(groups):
        if REFERENCE.match(label) or PRIVATE_OR_SENSITIVE_SECTION.search(label):
            continue
        for row, paragraph in enumerate(paragraphs[:3]):
            for sentence in SENTENCES.split(paragraph)[:3]:
                text = sentence.strip()
                if (not safe(text, 30, 112) or text in title or STALE_CLAIM.search(text)
                        or re.match(r"^(?:[•·]|我|其中|例如|该|此|这|同时|此外|所以|优点|缺点|然后|接着|下一步|本来|闲时)", text)
                        or not text.endswith(("。", "！", "？"))):
                    continue
                matches = OUTCOME.findall(text)
                if not matches and not WRAP_END.match(label):
                    continue
                score = (6 * bool(WRAP_END.match(label)) + min(3, len(matches)) * 2
                         + bool(SECTION_PRIORITY.search(label)) - row)
                candidates.append((-score, i, text, anchor))
    return min(candidates)[2:] if candidates else None


def body_link(anchor, label):
    return f'<a href="#{quote(anchor, safe="")}">{escape(label)}</a>'


def section_links(groups, excerpt_anchor=None):
    distinct = {}
    for i, (anchor, label, level, prose) in enumerate(groups):
        clean = re.sub(r"^(?:\d+(?:\.\d+)*[.、：:]?|[一二三四五六七八九十]+[.、：:])\s*", "", label)
        if (not safe(label, 3, 58, min_han=2) or DISQUALIFY.match(clean) or REFERENCE.match(label)
                or PRIVATE_OR_SENSITIVE_SECTION.search(label)):
            continue
        score = 3 * bool(SECTION_PRIORITY.search(label)) + 2 * (level == "h2") + bool(prose)
        score -= 4 * (anchor == excerpt_anchor)
        distinct.setdefault(label, (-score, i, anchor, label))
    chosen = sorted(sorted(distinct.values())[:3], key=lambda c: c[1])
    return "".join(f'<li>{body_link(anchor, label)}</li>' for _, _, anchor, label in chosen)


def card(post):
    body = BeautifulSoup(post.body, "lxml")
    heading = '<h2 id="reading-guide-title">本文速读</h2>'
    short = '<p>原文入口：<a href="#article-text">跳到正文</a></p>'
    key = Path(post.path).stem
    groups = fragments(body)

    if key in NOTES:
        takeaway, scope, expected = NOTES[key]
        anchors = {label: anchor for anchor, label, _, _ in groups}
        # Fall back to the live headings if an editor changes the cited original.
        if all(label in anchors for label in expected):
            links = "".join(f'<li>{body_link(anchors[label], label)}</li>' for label in expected)
            return ('<aside class="reading-guide" data-reading-kind="editorial" aria-labelledby="reading-guide-title">'
                    + heading + f'<p><strong>结论：</strong>{escape(takeaway)}</p>'
                    f'<p><strong>适用范围：</strong>{escape(scope)}</p>'
                    f'<nav aria-label="本文可核对的原文段落"><ul>{links}</ul></nav></aside>')

    if SENSITIVE_TOPIC.search(post.display_title) or HARD_RISK.search(post.search_text):
        topic = post.topic.name if post.topic else "技术笔记"
        return ('<aside class="reading-guide" data-reading-kind="restricted" aria-labelledby="reading-guide-title">'
                + heading + f'<p><strong>阅读范围：</strong>{escape(topic)}。涉及外部环境时，仅在获授权的场景中参考。</p>'
                + short + '</aside>')

    topic = post.topic
    # Retain a usable source map but avoid promoting personal anecdotes or time-sensitive claims as answers.
    prose_allowed = not topic or topic.name not in {"个人助手与上下文", "职业与实践"}
    excerpt = source_excerpt(groups, post.display_title) if prose_allowed else None
    scope = ""
    if topic:
        scope = f'<p class="reading-scope"><strong>主题：</strong><a href="{escape(topic.url)}">{escape(topic.name)}</a></p>'
    navigation = section_links(groups, excerpt[1] if excerpt else None)
    if excerpt:
        text, anchor = excerpt
        lead = f'<blockquote>{escape(text)} <cite>{body_link(anchor, "查看原文段落")}</cite></blockquote>'
    elif len(groups) == 1:
        tags = "、".join(name for name, _ in post.editorial_tags[:2] if safe(name, 2, 30))
        lead = f'<p><strong>涉及：</strong>{escape(tags)}。</p>' if tags else ""
    else:
        lead = ""
    if navigation:
        tail = f'<nav aria-label="可核对的原文段落"><ul>{navigation}</ul></nav>'
    elif not excerpt:
        # Image-first notes and short posts need a path to their real material, not invented prose.
        tail = ('<p><a href="#article-text">查看原文图示</a></p>'
                if body.img and len(post.search_text) < 120 else short)
    else:
        tail = ""
    kind = "excerpt" if excerpt else ("sections" if navigation else "short")
    return f'<aside class="reading-guide" data-reading-kind="{kind}" aria-labelledby="reading-guide-title">{heading}{lead}{tail}{scope}</aside>'
