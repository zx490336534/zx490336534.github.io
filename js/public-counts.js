'use strict';

(() => {
  const counters = [...document.querySelectorAll('[data-public-count]')];
  const popularList = document.querySelector('[data-popular-list]');
  if (!counters.length && !popularList) return;
  const showsLifetimeClicks = counters.some(counter => counter.dataset.publicCount === 'clicks');

  const digits = new Intl.NumberFormat('zh-CN');
  const dates = new Intl.DateTimeFormat('zh-CN', {dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Shanghai'});
  const wechatRows = popularList ? [...popularList.children] : [];
  let displayedAt = 0;

  function renderPopular(articles) {
    if (!popularList || !Array.isArray(articles) || !articles.length || popularList.contains(document.activeElement)) return;
    const rows = [];
    const seen = new Set();
    for (const article of articles) {
      if (!article || !/^\/article\/[a-z0-9-]+\.html$/.test(article.path) || seen.has(article.path) ||
          typeof article.title !== 'string' || !article.title.trim() || !Number.isSafeInteger(article.clicks) || article.clicks <= 0) continue;
      seen.add(article.path);
      const row = document.createElement('li');
      const link = document.createElement('a');
      link.href = article.path;
      if (typeof article.cover === 'string' && article.cover.startsWith('/images/')) {
        const image = document.createElement('img');
        image.className = 'post-thumbnail';
        image.src = article.cover;
        image.alt = '';
        image.width = 180;
        image.height = 90;
        image.loading = 'lazy';
        image.decoding = 'async';
        link.append(image);
      }
      const copy = document.createElement('span');
      const title = document.createElement('strong');
      title.textContent = article.title;
      const count = document.createElement('small');
      count.textContent = '累计点击 ' + digits.format(article.clicks);
      copy.append(title, count);
      link.append(copy);
      row.append(link);
      rows.push(row);
    }
    if (!rows.length) return;
    const hasWechatRows = rows.length < wechatRows.length;
    const fallback = wechatRows.filter(row => !seen.has(row.querySelector('a').getAttribute('href')));
    popularList.replaceChildren(...[...rows, ...fallback].slice(0, wechatRows.length));
    document.querySelector('[data-popular-basis]').textContent = hasWechatRows
      ? '按站内累计点击排序 · 公众号热读补位'
      : '按站内累计点击排序';
  }

  function render(data) {
    const updated = Date.parse(data.updatedAt);
    if (data.days !== 30 || !Number.isFinite(updated) || updated <= displayedAt ||
        !Number.isSafeInteger(data.clicks) || data.clicks < 0 ||
        (showsLifetimeClicks && !data.clickCheckpoint) ||
        !data.reads || typeof data.reads !== 'object' || Array.isArray(data.reads)) return;
    displayedAt = updated;
    for (const counter of counters) {
      const count = counter.dataset.publicCount === 'clicks' ? data.clicks : (data.reads[counter.dataset.articlePath] ?? 0);
      if (!Number.isSafeInteger(count) || count < 0) continue;
      counter.querySelector('strong').textContent = digits.format(count);
      counter.title = '统计更新于 ' + dates.format(updated);
      counter.hidden = false;
    }
    renderPopular(data.popularArticles);
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
