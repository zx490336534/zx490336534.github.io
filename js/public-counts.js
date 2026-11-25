'use strict';

(() => {
  const counters = [...document.querySelectorAll('[data-public-count]')];
  if (!counters.length) return;

  const digits = new Intl.NumberFormat('zh-CN');
  const dates = new Intl.DateTimeFormat('zh-CN', {dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Shanghai'});
  let displayedAt = 0;

  function render(data) {
    const updated = Date.parse(data.updatedAt);
    if (data.days !== 30 || !Number.isFinite(updated) || updated <= displayedAt ||
        !Number.isSafeInteger(data.clicks) || data.clicks < 0 ||
        !data.reads || typeof data.reads !== 'object' || Array.isArray(data.reads)) return;
    displayedAt = updated;
    for (const counter of counters) {
      const count = counter.dataset.publicCount === 'clicks' ? data.clicks : (data.reads[counter.dataset.articlePath] ?? 0);
      if (!Number.isSafeInteger(count) || count < 0) continue;
      counter.querySelector('strong').textContent = digits.format(count);
      counter.title = '统计更新于 ' + dates.format(updated);
      counter.hidden = false;
    }
  }

  function load(url) {
    fetch(url, {credentials: 'omit', referrerPolicy: 'no-referrer', signal: globalThis.AbortSignal?.timeout?.(4500)})
      .then(response => {
        if (!response.ok) throw new Error('No public counter data');
        return response.json();
      })
      .then(render)
      .catch(() => {});
  }

  load('/public-stats.json');
  load('https://raw.githubusercontent.com/zx490336534/zx490336534.github.io/refs/heads/codex/blog-public-counters/stats.json');
})();
