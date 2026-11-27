'use strict';

(() => {
  const counters = [...document.querySelectorAll('[data-public-count]')];
  const popularList = document.querySelector('[data-popular-list]');
  if (!counters.length && !popularList) return;
  const footerStats = document.querySelector('.footer-stats');
  const updatedTime = document.createElement('time');
  updatedTime.hidden = true;
  counters.at(-1)?.after(updatedTime);

  const digits = new Intl.NumberFormat('zh-CN');
  const dates = new Intl.DateTimeFormat('zh-CN', {dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Shanghai'});
  const cacheKey = 'blog.public-counts.v2';
  const articlePath = /^\/article\/[a-z0-9-]+\.html$/;
  const validCount = count => Number.isSafeInteger(count) && count >= 0;
  const wechatRows = popularList ? [...popularList.children] : [];
  let displayedAt = 0;
  let displayedRanking;

  function snapshot(data) {
    if (data?.version !== 2 || typeof data.updatedAt !== 'string' || !validCount(data.views) || !validCount(data.clicks)) return;
    const updated = Date.parse(data.updatedAt);
    if (!Number.isFinite(updated) || updated <= 0 || updated > Date.now() + 300_000 ||
        !data.reads || typeof data.reads !== 'object' || Array.isArray(data.reads) ||
        !Object.entries(data.reads).every(([path, count]) => articlePath.test(path) && validCount(count))) return;
    const popularArticles = [];
    for (const row of Array.isArray(data.popularArticles) ? data.popularArticles : []) {
      if (!row || typeof row.path !== 'string' || !articlePath.test(row.path) || typeof row.title !== 'string' ||
          !row.title.trim() || !validCount(row.clicks) || row.clicks === 0) continue;
      const cover = typeof row.cover === 'string' && row.cover.startsWith('/images/') ? row.cover : '';
      popularArticles.push({path: row.path, title: row.title, cover, clicks: row.clicks});
    }
    return {version: 2, updatedAt: data.updatedAt, views: data.views, clicks: data.clicks, reads: data.reads, popularArticles};
  }

  function cachedSnapshot() {
    try {
      return snapshot(JSON.parse(localStorage.getItem(cacheKey)));
    } catch {
      // Storage may be disabled or contain a partial value.
    }
  }

  function renderPopular(articles) {
    if (!popularList || !articles.length || popularList.contains(document.activeElement)) return;
    const ranking = JSON.stringify(articles);
    if (ranking === displayedRanking) return;
    const rows = [];
    const seen = new Set();
    for (const article of articles) {
      if (seen.has(article.path)) continue;
      seen.add(article.path);
      const row = document.createElement('li');
      const link = document.createElement('a');
      link.href = article.path;
      const rank = document.createElement('span');
      rank.className = 'list-rank';
      rank.setAttribute('aria-hidden', 'true');
      const thumb = document.createElement('span');
      thumb.className = 'popular-thumb';
      if (article.cover) {
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
    if (!data) return;
    const updated = Date.parse(data.updatedAt);
    if (updated < displayedAt) return;
    if (updated > displayedAt) {
      displayedAt = updated;
      for (const counter of counters) {
        const metric = counter.dataset.publicCount;
        const count = metric === 'reads' ? (data.reads[counter.dataset.articlePath] ?? 0) : data[metric];
        if (!Number.isSafeInteger(count) || count < 0) continue;
        counter.querySelector('strong').textContent = digits.format(count);
        counter.hidden = false;
      }
      updatedTime.dateTime = data.updatedAt;
      updatedTime.textContent = '统计更新于 ' + dates.format(updated) + '（北京时间）';
      updatedTime.hidden = false;
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
      .then(data => {
        const fresh = snapshot(data);
        if (!fresh) return;
        const cached = cachedSnapshot();
        if (cached && Date.parse(cached.updatedAt) >= Date.parse(fresh.updatedAt)) {
          render(cached);
          return;
        }
        render(fresh);
        if (Date.parse(fresh.updatedAt) === displayedAt) {
          try {
            localStorage.setItem(cacheKey, JSON.stringify(fresh));
          } catch {
            // The page can still display the snapshot when storage is unavailable.
          }
        }
      })
      .catch(() => {});
  }

  const statsUrl = new URL('https://raw.githubusercontent.com/zx490336534/zx490336534.github.io/refs/heads/codex/blog-public-counters/stats.json');
  const refreshInterval = 5 * 60_000;
  let timer;
  let pending = false;

  function refresh() {
    if (document.hidden || pending) return;
    pending = true;
    statsUrl.searchParams.set('period', Math.floor(Date.now() / refreshInterval));
    load(statsUrl).finally(() => { pending = false; });
  }

  function updateSchedule() {
    clearInterval(timer);
    if (document.hidden) return;
    refresh();
    timer = setInterval(refresh, refreshInterval);
  }

  render(cachedSnapshot());
  load('/public-stats.json');
  document.addEventListener('visibilitychange', updateSchedule);
  updateSchedule();
})();
