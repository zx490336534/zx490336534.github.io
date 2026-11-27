"""Generate topical next reads without rewriting the article or its series order."""

from collections import Counter
from html import escape
from pathlib import Path

from blog_geo import HARD_RISK, SENSITIVE_LINE, SENSITIVE_TOPIC
from blog_topics import tag_key

# Readers can follow a concrete question across categories when metadata alone
# would only find the next article about the same framework.
EVAL_NEXT = {
    "promptfoo-agent-regression": (
        ("kitaru-agent-replay-regression", "同一类回归如果要断言工具有没有被调用，该看什么？"),
        ("llm-judge-empty-output", "有了通过率，还要检查哪些样本抬高了分数？"),
    ),
    "kitaru-agent-replay-regression": (
        ("promptfoo-agent-regression", "先用几个可控反例检验一条断言是否有效。"),
        ("temporal-agent-recovery", "离线回放与故障恢复是两回事：保存重试后如何核对写入结果？"),
    ),
    "llm-judge-empty-output": (
        ("promptfoo-agent-regression", "当结果有明确业务约束，先用规则做可重复断言。"),
        ("agent-ui-testing", "界面显示成功但产物没保存时，回读比判断提示语更可靠。"),
    ),
    "agent-ui-testing": (
        ("temporal-agent-recovery", "从页面回读继续往下追：保存重试时验证最终写了几条。"),
        ("llm-judge-empty-output", "把没有产物和产物质量不佳分开报告。"),
    ),
    "temporal-agent-recovery": (
        ("kitaru-agent-replay-regression", "用记录检查 Agent 的动作历史，不把回放当成线上重试。"),
        ("agent-ui-testing", "从用户端回读产物，核对界面成功提示是否可信。"),
    ),
}


def build(posts, positions):
    eligible = [
        post for post in posts if post.topic and post.topic.key != "unclassified"
        and not SENSITIVE_TOPIC.search(post.display_title)
        and not SENSITIVE_LINE.search(post.display_title)
        and not HARD_RISK.search(post.search_text)
    ]
    by_slug = {Path(post.path).stem: post for post in eligible}
    labels = {p.path: {tag_key(name): name for name, _ in p.editorial_tags
                       if not SENSITIVE_LINE.search(name) and not SENSITIVE_TOPIC.search(name)}
              for p in eligible}
    counts = Counter(tag for tags in labels.values() for tag in tags)
    mapping = {}
    for index, source in enumerate(posts):
        if source.path not in labels:
            continue
        if position := positions.get(source.path):
            series, number = position
            adjacent = {series.chapters[i].path for i in (number - 2, number)
                        if 0 <= i < len(series.chapters)}
        else:
            adjacent = {posts[i].path for i in (index - 1, index + 1) if 0 <= i < len(posts)}
        tag_names = labels[source.path]
        manual = [(by_slug[key], why) for key, why in EVAL_NEXT.get(Path(source.path).stem, ())
                  if key in by_slug and by_slug[key].path not in adjacent]
        chosen = {target.path for target, _ in manual}
        ranked = []
        for target in eligible:
            if source.path == target.path or target.path in chosen or target.path in adjacent:
                continue
            same_topic = source.topic.key == target.topic.key
            # Cross-category suggestions must share a specific editorial tag.
            shared = sorted((tag for tag in tag_names.keys() & labels[target.path].keys()
                             if counts[tag] <= 18), key=lambda tag: (counts[tag], tag))
            if not same_topic and not shared:
                continue
            why = "共同主题：" + "、".join(tag_names[tag] for tag in shared[:2]) if shared else ""
            ranked.append((not bool(shared), not same_topic, -len(shared),
                           sum(counts[tag] for tag in shared), target.path, target, why))
        # At most three next reads. Preserve a useful category link if there
        # isn't a defensible article match.
        automatic = [(row[-2], row[-1]) for row in sorted(ranked)[:3 - len(manual)]]
        mapping[source.path] = (source.topic, manual + automatic)
    return mapping


def render(result):
    if not result:
        return ""
    topic, links = result
    rows = "".join(
        f'<li><a href="{escape(post.path)}">{escape(post.display_title)}</a>'
        + (f'<p>{escape(why)}</p>' if why else "") + "</li>"
        for post, why in links
    )
    items = f'<ul>{rows}</ul>' if rows else ""
    return ('<nav class="read-next" aria-labelledby="read-next-title"><h2 id="read-next-title">延伸阅读</h2>'
            f'{items}<a class="read-next-topic" href="{escape(topic.url)}">浏览「{escape(topic.name)}」分类</a></nav>')
