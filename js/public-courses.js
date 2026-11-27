'use strict';
(() => {
  const root = document.querySelector(".public-course");
  if (!root) return;
  const { course, current } = root.dataset;
  const storageKey = 'public-course-v1-' + course;
  const read = () => {
    try {
      const data = JSON.parse(localStorage.getItem(storageKey) || '{}');
      return { done: Array.isArray(data.done) ? data.done.filter(x => typeof x === 'string') : [],
               last: typeof data.last === 'string' ? data.last : '' };
    } catch { return { done: [], last: '' }; }
  };
  const save = data => {
    try { localStorage.setItem(storageKey, JSON.stringify(data)); return true; }
    catch { return false; }
  };
  const input = document.querySelector('#filter');
  const tiles = [...document.querySelectorAll('[data-lesson]')];
  if (input) {
    document.querySelector('#filter-controls').hidden = false;
    const stages = [...document.querySelectorAll('.map .stage')];
    const jumps = [...document.querySelectorAll('.jump a')];
    const normalize = value => value.normalize('NFKC').toLocaleLowerCase().trim();
    const searchable = tiles.map(tile => [tile, normalize(tile.textContent + ' ' + tile.dataset.keywords)]);
    const refresh = () => {
      const parts = normalize(input.value).split(/\s+/u).filter(Boolean);
      for (const [tile, text] of searchable) tile.hidden = !parts.every(part => text.includes(part));
      for (const stage of stages) stage.hidden = !stage.querySelector('.lesson-tile:not([hidden])');
      for (const jump of jumps) jump.hidden = document.getElementById(jump.hash.slice(1)).hidden;
      const visible = tiles.filter(tile => !tile.hidden).length;
      document.querySelector('.map .empty').hidden = Boolean(visible);
      document.querySelector('#filter-status').textContent = '显示 ' + visible + ' 节课';
    };
    input.addEventListener('input', event => { if (!event.isComposing) refresh(); });
    input.addEventListener('compositionend', refresh);
    document.querySelector('#clear-filter').addEventListener('click', () => {
      input.value = ''; refresh(); input.focus();
    });
    const showProgress = () => {
      const data = read();
      const done = new Set(data.done);
      let count = 0;
      for (const tile of tiles) {
        const isDone = done.has(tile.dataset.lesson);
        tile.querySelector('.lesson-state').textContent = isDone ? '已学' : '';
        count += Number(isDone);
      }
      const next = tiles.find(tile => tile.dataset.lesson === data.last && !done.has(data.last))
        || tiles.find(tile => !done.has(tile.dataset.lesson));
      const resume = document.querySelector('#resume');
      const destination = (next || tiles[0]).querySelector('a');
      resume.setAttribute('href', destination.getAttribute('href'));
      resume.textContent = count === tiles.length ? '从头复习' : (data.last || count ? '继续学习' : '从第 1 课开始');
      const bar = document.querySelector('#progress-text');
      bar.hidden = false;
      bar.textContent = '本设备学习进度：' + count + ' / ' + tiles.length;
    };
    showProgress();
    window.addEventListener('pageshow', showProgress);
    window.addEventListener('storage', event => {
      if (event.key === storageKey || event.key === null) showProgress();
    });
  }
  const complete = document.querySelector('#complete-lesson');
  if (current && complete) {
    let data = read();
    data.last = current;
    save(data);
    const update = () => {
      const done = data.done.includes(current);
      complete.textContent = done ? '撤销已学标记' : '标记为已学';
      complete.setAttribute('aria-pressed', String(done));
    };
    complete.hidden = false;
    update();
    complete.addEventListener('click', () => {
      data.done = data.done.includes(current) ? data.done.filter(x => x !== current) : [...data.done, current];
      const saved = save(data);
      update();
      document.querySelector('#complete-status').textContent = saved ? '本设备进度已更新。' : '浏览器不允许保存，刷新后不会保留。';
    });
  }
  const copy = root.querySelector('[data-copy-example]');
  if (copy && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    copy.hidden = false;
    copy.addEventListener('click', async () => {
      const block = copy.closest('.snippet');
      const status = block.querySelector('[role=status]');
      try {
        await navigator.clipboard.writeText(block.querySelector('pre code').textContent);
        status.textContent = '已复制';
      } catch {
        status.textContent = '复制未成功，请手动选中代码。';
      }
    });
  }
  const quiz = document.querySelector('.course-quiz');
  if (quiz) {
    quiz.hidden = false;
    quiz.addEventListener('submit', event => {
      event.preventDefault();
      const picked = new FormData(quiz).get('check');
      if (picked === null) return;
      const correct = picked === quiz.dataset.answer;
      const result = quiz.querySelector('.quiz-result');
      result.dataset.state = correct ? 'correct' : 'wrong';
      result.textContent = correct ? quiz.dataset.right : quiz.dataset.wrong;
    });
  }
  const lab = document.querySelector('[data-lab]');
  if (lab) {
    lab.hidden = false;
    lab.addEventListener('click', event => {
      const choice = event.target.closest('button[data-run]');
      if (!choice) return;
      const fault = choice.dataset.run === 'fault';
      let lines;
      if (lab.dataset.lab === 'layout-start') {
        const accepted = { taskId: 'demo-123', state: 'accepted' };
        const result = { taskId: 'demo-123', state: fault ? 'failed' : 'done', revision: 3 };
        const updated = result.taskId === accepted.taskId && result.state === 'done';
        lines = [
          '① 浏览器：提交「生成布局」',
          '② 服务：' + accepted.taskId + ' 已接收（还没完成）',
          '③ 后台：' + (updated ? '校验通过，输出版本 ' + result.revision : '草案校验失败'),
          '④ 页面：' + (updated ? '二维、三维一起更新为版本 ' + result.revision : '保留旧布局，显示错误'),
        ];
      } else if (lab.dataset.lab === 'test-start') {
        const cases = ['pass', 'pass', fault ? 'infrastructure_error' : 'pass'];
        const passed = cases.filter(state => state === 'pass').length;
        lines = [
          '① 提交 3 条用例 → 运行 sample-42 已排队',
          '② 执行器：' + (fault ? '第 3 条未拿到运行环境' : '依次运行三条用例'),
          '③ 汇总：' + passed + ' 条通过，' + (fault ? '1 条执行异常，不计入断言失败' : '0 条异常'),
        ];
      } else if (lab.dataset.lab === 'layout-fault') {
        let snapshot = { id: 'sample-2', seq: 2, revision: 3 };
        const next = fault ? { id: 'sample-1', seq: 9, revision: 8 } : { id: 'sample-2', seq: 3, revision: 4 };
        const accepted = next.id === snapshot.id && next.seq === snapshot.seq + 1;
        if (accepted) snapshot = next;
        lines = [`事件：${next.id}（序号 ${next.seq}）`, accepted ? '接收当前任务的下一条事件' : '忽略旧任务：序号再大也不能覆盖',
                 `二维 / 三维视图：版本 ${snapshot.revision}`];
      } else {
        const answer = 'ask_confirm';
        const trace = fault ? ['save_booking'] : [];
        const answerPassed = answer === 'ask_confirm';
        const policyPassed = !trace.includes('save_booking');
        lines = [`答复：${answer} → ${answerPassed ? '通过' : '失败'}`,
                 `工具轨迹：${trace.join(', ') || '未调用写工具'} → ${policyPassed ? '通过' : '失败'}`,
                 `发布门槛：${answerPassed && policyPassed ? '通过' : '拦截'}`];
      }
      lab.querySelector('output').textContent = lines.join('\n');
    });
  }
})();
