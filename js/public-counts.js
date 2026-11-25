'use strict';

(() => {
  const counters = [...document.querySelectorAll('[data-public-count]')];
  const popularList = document.querySelector('[data-popular-list]');
  if (!counters.length && !popularList) return;
  const footerStats = document.querySelector('.footer-stats');

  const digits = new Intl.NumberFormat('zh-CN');
  const dates = new Intl.DateTimeFormat('zh-CN', {dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Shanghai'});
  const wechatRows = popularList ? [...popularList.children] : [];
  let displayedAt = 0;
  let displayedRanking;

  function renderPopular(articles) {
    if (!popularList || !Array.isArray(articles) || !articles.length || popularList.contains(document.activeElement)) return;
    const ranking = JSON.stringify(articles);
    if (ranking === displayedRanking) return;
    const rows = [];
    const seen = new Set();
    for (const article of articles) {
      if (!article || !/^\/article\/[a-z0-9-]+\.html$/.test(article.path) || seen.has(article.path) ||
          typeof article.title !== 'string' || !article.title.trim() || !Number.isSafeInteger(article.clicks) || article.clicks <= 0) continue;
      seen.add(article.path);
      const row = document.createElement('li');
      const link = document.createElement('a');
      link.href = article.path;
      const rank = document.createElement('span');
      rank.className = 'list-rank';
      rank.setAttribute('aria-hidden', 'true');
      const thumb = document.createElement('span');
      thumb.className = 'popular-thumb';
      if (typeof article.cover === 'string' && article.cover.startsWith('/images/')) {
        const image = document.createElement('img');
        image.className = 'post-thumbnail';
        image.src = article.cover;
        image.alt = '';
        image.width = 180;
        image.height = 90;
        image.loading = 'lazy';
        image.decoding = 'async';
        thumb.append(image);
      }
      const copy = document.createElement('span');
      copy.className = 'popular-copy';
      const title = document.createElement('strong');
      title.textContent = article.title;
      const count = document.createElement('small');
      count.textContent = '累计点击 ' + digits.format(article.clicks);
      copy.append(title, count);
      link.append(rank, thumb, copy);
      row.append(link);
      rows.push(row);
    }
    if (!rows.length) return;
    displayedRanking = ranking;
    const hasWechatRows = rows.length < wechatRows.length;
    const fallback = wechatRows.filter(row => !seen.has(row.querySelector('a').getAttribute('href')));
    popularList.replaceChildren(...[...rows, ...fallback].slice(0, wechatRows.length));
    document.querySelector('[data-popular-basis]').textContent = hasWechatRows
      ? '按站内累计点击排序 · 公众号热读补位'
      : '按站内累计点击排序';
  }

  function render(data) {
    if (data?.version !== 2) return;
    const updated = Date.parse(data.updatedAt);
    if (!Number.isFinite(updated) || updated < displayedAt ||
        !Number.isSafeInteger(data.clicks) || data.clicks < 0 ||
        !Number.isSafeInteger(data.views) || data.views < 0 ||
        !data.reads || typeof data.reads !== 'object' || Array.isArray(data.reads)) return;
    if (updated > displayedAt) {
      displayedAt = updated;
      for (const counter of counters) {
        const metric = counter.dataset.publicCount;
        const count = metric === 'reads' ? (data.reads[counter.dataset.articlePath] ?? 0) : data[metric];
        if (!Number.isSafeInteger(count) || count < 0) continue;
        counter.querySelector('strong').textContent = digits.format(count);
        counter.title = '统计更新于 ' + dates.format(updated);
        counter.hidden = false;
      }
      if (footerStats) footerStats.hidden = false;
    }
    renderPopular(data.popularArticles);
  }

  function load(url) {
    return fetch(url, {credentials: 'omit', referrerPolicy: 'no-referrer', signal: globalThis.AbortSignal?.timeout?.(4500)})
      .then(response => {
        if (!response.ok) throw new Error('No public counter data');
        return response.json();
      })
      .then(render)
      .catch(() => {});
  }

  const statsUrl = new URL('https://raw.githubusercontent.com/zx490336534/zx490336534.github.io/refs/heads/codex/blog-public-counters/stats.json');
  const refreshInterval = 60_000;
  let timer;
  let pending = false;

  function refresh() {
    if (document.hidden || pending) return;
    pending = true;
    statsUrl.searchParams.set('minute', Math.floor(Date.now() / refreshInterval));
    load(statsUrl).finally(() => { pending = false; });
  }

  function updateSchedule() {
    clearInterval(timer);
    if (document.hidden) return;
    refresh();
    timer = setInterval(refresh, refreshInterval);
  }

  load('/public-stats.json');
  document.addEventListener('visibilitychange', updateSchedule);
  updateSchedule();
})();
