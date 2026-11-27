"""Render the two public learning maps and all their lessons deterministically."""
from html import escape
from pathlib import Path
from course_curriculum import AI, QA, TERMS

ROOT = Path(__file__).resolve().parents[1]
COURSES = (
    ("teaching-aihom", "AI 应用全栈实战", "从一次布局生成，学会前后端联调与 Agent 故障恢复。",
     "用虚构的 RoomLab 串起界面、任务服务、Agent 和二维／三维视图。适合想从测试进入 AI 应用开发的人。", AI),
    ("teaching-kuai", "AI 测试平台与评测实战", "从批量测试出发，走到 Agent 用例生成与可复现评测。",
     "用虚构的 CaseLab 拆开调度、执行、看板与评分。适合测试开发，也适合想把 AI 评测做成工程能力的人。", QA),
)
STAGES = (
    ("foundation", "01 · 先跑通", "先认清链路、角色和状态，不急着接真实模型。", 0, 2),
    ("engineering", "02 · 拆开关键机制", "把最容易藏问题的边界拿出来单独验证。", 2, 6),
    ("practice", "03 · 验证与交付", "练习定位失败，最后交付可复现的实战报告。", 6, 8),
)

def page(shell, slug, title, description, path, body, label, current):
    course_path = f"/{slug}/lessons/{path}"
    extra_head = ('<link rel="stylesheet" href="/css/public-courses.css">\n  '
                  '<script src="/js/public-courses.js" defer></script>')
    content = (f'<div class="public-course" data-course="{slug}" data-current="{current}">'
               f'{body}</div>')
    return shell(title, course_path, content, description, extra_head)

def lesson_href(item):
    return f"{item[0]}.html"

def breadcrumbs(label=None):
    part = f'<a href="index.html">{escape(label)}</a>' if label else '<span aria-current="page">学习地图</span>'
    return f'<div class="breadcrumbs"><a href="/lab/">工具与课程</a><span aria-hidden="true">/</span>{part}</div>'

def course_map(shell, slug, label, intro, audience, lessons):
    total = sum(m[2] for m in lessons)
    stage_html = []
    for stage, title, subtitle, start, stop in STAGES:
        cards = ''
        for i, item in enumerate(lessons[start:stop], start + 1):
            key, name, mins, goal, *_ = item
            cards += f"""<li class="lesson-tile" data-lesson="{key}">
  <a href="{lesson_href(item)}"><span class="lesson-num">{i:03}</span><span class="lesson-text"><strong>{escape(name)}</strong><span>{escape(goal)}</span></span><span class="lesson-end"><span>{mins} 分钟</span><span class="lesson-state"></span><span aria-hidden="true">↗</span></span></a>
</li>"""
        stage_html.append(f'<section class="stage" id="stage-{stage}"><h2>{title}</h2><p>{subtitle}</p><ol class="lesson-list">{cards}</ol></section>')
    jumps = "".join(f'<a href="#stage-{stage}">{title.split(" · ")[-1]}</a>' for stage, title, *_ in STAGES)
    other = next((s, name) for s, name, *_ in COURSES if s != slug)
    body = f"""{breadcrumbs()}
    <section class="hero">
      <div class="hero-copy"><p class="eyebrow">公开学习地图 / 项目驱动</p><h1>{escape(label)}</h1>
      <p class="lead">{escape(intro)}</p><p>{escape(audience)}</p>
      <p class="stats"><span>{len(lessons)} 节</span><span>约 {total} 分钟</span></p>
      <div class="actions"><a class="button primary" id="resume" href="{lesson_href(lessons[0])}">从第 1 课开始</a><a class="button" href="{lesson_href(lessons[-1])}">直接看实战</a></div></div>
      <aside class="learning-note"><p class="eyebrow">怎么学</p><h2>每节先解决一个问题</h2><ol><li>读一个场景，跟着走一遍。</li><li>做自测，核对判断依据。</li><li>用小练习写下可观察的结果。</li></ol><p id="progress-text" hidden></p></aside>
    </section>
    <div class="course-tools"><div id="filter-controls" hidden><label for="filter">筛选课程</label><div class="search-row"><input type="search" id="filter" placeholder="如：恢复、评测、003"><button type="button" id="clear-filter">清空</button></div><p class="sr-only" id="filter-status" role="status"></p></div><nav class="jump" aria-label="课程阶段">{jumps}</nav></div>
    <div class="map">{''.join(stage_html)}<div class="empty" hidden><h2>没有找到相符课程</h2><p>试试更短的关键词，或者清空筛选看完整路线。</p></div></div>
    <aside class="related"><span>继续拓展</span><a href="/{other[0]}/lessons/index.html">{escape(other[1])} →</a></aside>"""
    return page(shell, slug, label, intro, "index.html", body, label, "")

def lesson_page(shell, slug, label, lessons, i):
    key, title, mins, goal, scene, steps, sample, exercise, question, options, answer, reason = lessons[i]
    step_html = "".join(f"<li>{escape(step)}</li>" for step in steps)
    rejected = "这个选项不成立。再想想："
    option_html = "".join(
        f'<label><input type="radio" name="check" value="{idx}" required> {escape(option)}</label>'
        for idx, option in enumerate(options))
    term, meaning = TERMS[slug][key]
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
    body = f"""{breadcrumbs(label)}
    <header class="lesson-head"><p class="eyebrow">第 {i+1:02} / {len(lessons):02} 课 · {mins} 分钟</p><h1>{escape(title)}</h1><p class="lead">{escape(goal)}</p></header>
    <div class="reading">
      <nav class="reading-toc" aria-label="本课目录"><a href="#scene">先看场景</a><a href="#walkthrough">走一遍</a><a href="#exercise">动手练习</a><a href="#check">自测</a></nav>
      <article class="lesson-content">
        <section id="scene"><h2>先看场景</h2><p>{escape(scene)}</p><p class="course-term"><strong>{escape(term)}：</strong>{escape(meaning)}</p></section>
        <section id="walkthrough"><h2>走一遍</h2><ol class="steps">{step_html}</ol><details class="snippet" open><summary>合成示例 <span>可折叠</span></summary><pre><code>{escape(sample)}</code></pre></details></section>
        <section id="exercise"><h2>动手练习</h2><p>{escape(exercise)}</p>{lab}</section>
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
    return page(shell, slug, title, goal, lesson_href(lessons[i]), body, label, key)

def build_courses(shell):
    # Only generated public materials are written; the private projects are not build inputs.
    for slug, label, intro, audience, lessons in COURSES:
        directory = ROOT / slug / "lessons"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.html").write_text(course_map(shell, slug, label, intro, audience, lessons), encoding="utf-8")
        for i, lesson in enumerate(lessons):
            (directory / lesson_href(lesson)).write_text(lesson_page(shell, slug, label, lessons, i), encoding="utf-8")
