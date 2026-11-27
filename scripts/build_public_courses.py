"""Render the two public learning maps and all their lessons deterministically."""
from html import escape
from pathlib import Path
from course_curriculum import AI, QA, TERMS as CORE_TERMS
from course_code_walkthroughs import AI_DEPTH, QA_DEPTH
from course_roomlab_extension import ROOMLAB_EXTRA
from course_caselab_extension import CASELAB_EXTRA
from course_learning_paths import PATHS
from course_extra_workshops import ROOM_WORKSHOPS, CASE_WORKSHOPS

ROOT = Path(__file__).resolve().parents[1]
CORE_COURSES = (
    ("teaching-aihom", "AI 应用全栈实战", "从一次布局生成，学会前后端联调与 Agent 故障恢复。",
     "用虚构的 RoomLab 串起界面、任务服务、Agent 和二维／三维视图。适合想从测试进入 AI 应用开发的人。", AI),
    ("teaching-kuai", "AI 测试平台与评测实战", "从批量测试出发，走到 Agent 用例生成与可复现评测。",
     "用虚构的 CaseLab 拆开调度、执行、看板与评分。适合测试开发，也适合想把 AI 评测做成工程能力的人。", QA),
)
EXTRAS = {
    "teaching-aihom": ROOMLAB_EXTRA | ROOM_WORKSHOPS,
    "teaching-kuai": CASELAB_EXTRA | CASE_WORKSHOPS,
}
_DEEP_CORE = {"teaching-aihom": AI_DEPTH, "teaching-kuai": QA_DEPTH}
_DEEP_MIN_CORE = (13, 15, 17, 17, 16, 16, 16, 25)
LABS = {
    "teaching-aihom": ("roomlab.py", "RoomLab", "RoomLab: all regression checks passed."),
    "teaching-kuai": ("caselab.py", "CaseLab", "CaseLab: all regression checks passed."),
}
COURSES = []
TERMS, DEEP, DURATION, STAGES = {}, {}, {}, {}


def assemble_course(slug, core, stages, extra):
    original = {record[0]: record for record in core}
    overlap = set(original) & set(extra)
    if overlap:
        raise ValueError(f"Existing lesson keys cannot be reused: {sorted(overlap)}")
    index = original | {key: data[0] for key, data in extra.items()}
    ordered = [key for _, _, _, keys in stages for key in keys]
    if len(ordered) != len(index) or set(ordered) != set(index):
        raise ValueError(f"Invalid stage plan for {slug}; missing {set(index) - set(ordered)}, unknown {set(ordered) - set(index)}")
    if any(index[key][0] != key for key in ordered):
        raise ValueError(f"Mismatched lesson route for {slug}")
    return [index[key] for key in ordered]


for slug, label, intro, audience, core in CORE_COURSES:
    extra = EXTRAS[slug]
    STAGES[slug] = PATHS[slug]
    lessons = assemble_course(slug, core, STAGES[slug], extra)
    COURSES.append((slug, label, intro, audience, lessons))
    TERMS[slug] = CORE_TERMS[slug] | {key: data[1] for key, data in extra.items()}
    DEEP[slug] = _DEEP_CORE[slug] | {key: data[2] for key, data in extra.items()}
    core_deep = dict(zip((record[0] for record in core), _DEEP_MIN_CORE))
    DURATION[slug] = {record[0]: record[2] + core_deep.get(record[0], 14) for record in lessons}


def page(shell, slug, title, description, path, body, current):
    course_path = f"/{slug}/lessons/{path}"
    extra_head = ('<link rel="stylesheet" href="/css/public-courses.css?v=extended-path-1">\n  '
                  '<script src="/js/public-courses.js?v=extended-path-1" defer></script>')
    content = (f'<div class="public-course" data-course="{slug}" data-current="{current}">'
               f'{body}</div>')
    return shell(title, course_path, content, description, extra_head)

def lesson_href(item):
    return f"{item[0]}.html"

def breadcrumbs(label=None):
    part = f'<a href="index.html">{escape(label)}</a>' if label else '<span aria-current="page">学习地图</span>'
    return f'<div class="breadcrumbs"><a href="/lab/">工具与课程</a><span aria-hidden="true">/</span>{part}</div>'

def course_map(shell, slug, label, intro, audience, lessons):
    index = {item[0]: (i, item) for i, item in enumerate(lessons, 1)}
    stage_html = []
    for number, (stage, title, subtitle, keys) in enumerate(STAGES[slug], 1):
        cards = ''
        for key in keys:
            i, item = index[key]
            _, name, _, goal, *_ = item
            term = TERMS[slug][key][0]
            cards += f"""<li class="lesson-tile" data-lesson="{key}" data-keywords="{escape(term, quote=True)}">
  <a href="{lesson_href(item)}"><span class="lesson-num">{i:03}</span><span class="lesson-text"><strong>{escape(name)}</strong><span>{escape(goal)}</span></span><span class="lesson-end"><span>{DURATION[slug][key]} 分钟</span><span class="lesson-state"></span><span aria-hidden="true">↗</span></span></a>
</li>"""
        stage_html.append(f'<section class="stage" id="stage-{stage}"><p class="stage-index">阶段 {number:02}</p><h2>{escape(title)}</h2><p>{escape(subtitle)}</p><ol class="lesson-list">{cards}</ol></section>')
    jumps = "".join(f'<a href="#stage-{stage}">{escape(title)}</a>' for stage, title, *_ in STAGES[slug])
    other = next((s, name) for s, name, *_ in COURSES if s != slug)
    body = f"""{breadcrumbs()}
    <section class="hero">
      <div class="hero-copy"><p class="eyebrow">公开学习地图 / 项目驱动</p><h1>{escape(label)}</h1>
      <p class="lead">{escape(intro)}</p><p>{escape(audience)}</p>
      <div class="actions"><a class="button primary" id="resume" href="{lesson_href(lessons[0])}">从第 1 课开始</a><a class="button" href="#stage-practice">直接看实战</a></div></div>
      <aside class="learning-note"><p class="eyebrow">怎么学</p><h2>每一节，分两遍读</h2><ol><li><strong>第一遍跑通：</strong>从一个场景出发，画出正常调用链。</li><li><strong>第二遍读代码：</strong>顺着输入、分支和状态查到结果，用失败用例验证。</li><li><strong>最后做实战：</strong>跑示例项目，对照测试断言。</li></ol><p id="progress-text" hidden></p></aside>
    </section>
    <div class="course-tools"><div id="filter-controls" hidden><label for="filter">筛选课程</label><div class="search-row"><input type="search" id="filter" placeholder="如：恢复、评测、003"><button type="button" id="clear-filter">清空</button></div><p class="sr-only" id="filter-status" role="status"></p></div><nav class="jump" aria-label="课程阶段">{jumps}</nav></div>
    <div class="map">{''.join(stage_html)}<div class="empty" hidden><h2>没有找到相符课程</h2><p>试试更短的关键词，或者清空筛选看完整路线。</p></div></div>
    <aside class="related"><span>继续拓展</span><a href="/{other[0]}/lessons/index.html">{escape(other[1])} →</a></aside>"""
    return page(shell, slug, label, intro, "index.html", body, "")

def code_walkthrough(slug, key):
    question, flow, walkthrough, language, code, failures, assertions, recap = DEEP[slug][key]
    code_label, run_hint = {
        "javascript": ("JavaScript", "可复制到 lesson.cjs，再运行 node lesson.cjs。"),
        "python": ("Python", "可复制到 lesson.py，再运行 python3 lesson.py。"),
        "typescript": ("TypeScript", "可复制到 lesson.ts，再用 Node.js 24 运行 node lesson.ts。"),
        "sql": ("SQL", "对照逻辑和约束阅读，表结构以示例为准。"),
        "java": ("Java", "对照函数的输入、异常分支和末尾的断言。"),
    }.get(language.lower(), (language, "对照调用链阅读示例。"))
    flows = "".join(f'<li>{escape(step)}</li>' for step in flow)
    explanations = "".join(f'<div><h3>{escape(title)}</h3><p>{escape(text)}</p></div>' for title, text in walkthrough)
    cases = "".join(
        f'<div class="failure-card"><dt>{escape(name)}</dt><dd><strong>怎么触发：</strong>{escape(trigger)}</dd>'
        f'<dd><strong>怎么判断：</strong>{escape(expected)}</dd></div>'
        for name, trigger, expected in failures
    )
    checks = "".join(f'<li>{escape(check)}</li>' for check in assertions)
    return f"""<section id="code-walkthrough" class="code-walkthrough">
          <p class="eyebrow">第二遍 · 把代码读懂</p><h2>代码拆解</h2><p class="code-question">{escape(question)}</p>
          <h3>调用链</h3><ol class="course-flow">{flows}</ol>
          <details class="snippet" open><summary>{escape(code_label)} 示例 <span>可折叠</span></summary>
            <div class="course-code-tools"><p>{escape(run_hint)}</p><button type="button" data-copy-example hidden>复制代码</button><span role="status"></span></div>
            <pre><code>{escape(code)}</code></pre>
          </details>
          <div class="code-notes">{explanations}</div>
        </section>
        <section id="failure-cases" class="code-walkthrough">
          <h2>复现失败</h2><dl class="failure-cards">{cases}</dl>
          <h3>写下这些测试断言</h3><ul class="course-assertions">{checks}</ul>
          <p class="course-term"><strong>这一课带走：</strong>{escape(recap)}</p>
        </section>"""


def reference_project(slug):
    filename, name, expected = LABS[slug]
    return f"""<aside class="reference-project">
      <h3>可运行练习：{name}</h3>
      <p>把示例保存到一个目录，在那个目录执行这行命令。先跑通，再删改一条保护规则，看哪项断言失败。</p>
      <p><a class="button primary" href="../examples/{filename}" download>下载 {filename}</a></p>
      <pre><code>python3 {filename}</code></pre>
      <p>全部检查通过时，会输出 <code>{expected}</code></p>
    </aside>"""


def lesson_page(shell, slug, label, lessons, i):
    key, title, mins, goal, scene, steps, sample, exercise, question, options, answer, reason = lessons[i]
    step_html = "".join(f"<li>{escape(step)}</li>" for step in steps)
    rejected = "这个选项不成立。再想想："
    option_html = "".join(
        f'<label><input type="radio" name="check" value="{idx}" required> {escape(option)}</label>'
        for idx, option in enumerate(options))
    term, meaning = TERMS[slug][key]
    advanced = code_walkthrough(slug, key)
    previous = lessons[i-1] if i else None
    following = lessons[i+1] if i+1 < len(lessons) else None
    prev_html = f'<a href="{lesson_href(previous)}" rel="prev">← {escape(previous[1])}</a>' if previous else '<span></span>'
    next_html = f'<a href="{lesson_href(following)}" rel="next">{escape(following[1])} →</a>' if following else '<a href="index.html">完成后回到地图 →</a>'
    demos = {
        ("teaching-aihom", "request"): ("layout-start", "从提交到预览"),
        ("teaching-kuai", "job"): ("test-start", "从提交到回归结果"),
        ("teaching-aihom", "capstone"): ("layout-fault", "收到旧任务的完成事件"),
        ("teaching-kuai", "capstone"): ("eval-fault", "正确答复却提前调用写入工具"),
    }
    demo = demos.get((slug, key))
    scene_id, exercise_title = demo or ("", "")
    lab = f"""<aside class="mini-lab" data-lab="{scene_id}" hidden><h3>动手试一下：{exercise_title}</h3>
      <p>这是浏览器里的合成数据演示，不连外部服务。</p>
      <div class="actions"><button type="button" data-run="normal">运行基线</button><button type="button" data-run="fault">注入故障</button></div>
      <pre><output aria-live="polite">选择一个场景开始。</output></pre></aside>""" if demo else ""
    project = reference_project(slug) if key == "capstone" else ""
    stage = next((stage_id, title) for stage_id, title, _, keys in STAGES[slug] if key in keys)
    intro_lab, exercise_lab = (lab, "") if i == 0 else ("", lab)
    body = f"""{breadcrumbs(label)}
    <header class="lesson-head"><p class="eyebrow"><a href="index.html#stage-{stage[0]}">{escape(stage[1])}</a> · 第 {i+1:02} 课 · 约 {DURATION[slug][key]} 分钟</p><h1>{escape(title)}</h1><p class="lead">{escape(goal)}</p></header>
    <div class="reading">
      <nav class="reading-toc" aria-label="本课目录"><a href="#scene">先看场景</a><a href="#walkthrough">走一遍</a><a href="#code-walkthrough">读代码</a><a href="#failure-cases">复现失败</a><a href="#exercise">动手练习</a><a href="#check">自测</a></nav>
      <article class="lesson-content">
        <section id="scene"><h2>先看场景</h2><p>{escape(scene)}</p><p class="course-term"><strong>{escape(term)}：</strong>{escape(meaning)}</p></section>
        <section id="walkthrough"><h2>走一遍</h2><ol class="steps">{step_html}</ol><details class="snippet" open><summary>合成示例 <span>可折叠</span></summary><pre><code>{escape(sample)}</code></pre></details>{intro_lab}</section>
        {advanced}
        <section id="exercise"><h2>动手练习</h2><p>{escape(exercise)}</p>{exercise_lab}{project}</section>
        <section id="check"><h2>自测</h2>
          <form class="course-quiz" data-answer="{answer}" data-right="答对了。{escape(reason, quote=True)}" data-wrong="{rejected}{escape(reason, quote=True)}" hidden>
            <fieldset><legend>{escape(question)}</legend>{option_html}</fieldset>
            <button type="submit">核对答案</button><p role="status" class="quiz-result"></p>
          </form>
          <noscript><p>{escape(question)}</p><details><summary>查看答案</summary><p>{escape(options[answer])}。{escape(reason)}</p></details></noscript>
        </section>
        <div class="completion"><button type="button" id="complete-lesson" aria-pressed="false" hidden>标记为已学</button><p role="status" id="complete-status"></p></div>
      </article>
    </div>
    <nav class="pagination" aria-label="课程分页">{prev_html}<a href="index.html">学习地图</a>{next_html}</nav>"""
    return page(shell, slug, title, goal, lesson_href(lessons[i]), body, key)

def build_courses(shell):
    # Only generated public materials are written; the private projects are not build inputs.
    for slug, label, intro, audience, lessons in COURSES:
        directory = ROOT / slug / "lessons"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.html").write_text(course_map(shell, slug, label, intro, audience, lessons), encoding="utf-8")
        for i, lesson in enumerate(lessons):
            (directory / lesson_href(lesson)).write_text(lesson_page(shell, slug, label, lessons, i), encoding="utf-8")
