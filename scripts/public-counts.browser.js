async ({api, slug, website, articles, previous}) => {
  async function get(path, headers = {}) {
    const response = await fetch(api + path, {
      headers: {Accept: 'application/json', ...headers},
      credentials: 'omit',
      cache: 'no-store',
      signal: AbortSignal.timeout(12000),
    });
    if (!response.ok) throw new Error('Umami reported HTTP ' + response.status);
    return response.json();
  }

  const share = await get('/share/' + encodeURIComponent(slug));
  if (share.websiteId !== website || !share.token) throw new Error('Unexpected read-only Umami resource');
  const auth = {'x-umami-share-context': '1', 'x-umami-share-token': share.token};
  const day = 86400000;
  const end = Date.now();
  const firstDay = Date.UTC(2026, 10, 25);
  const checkpoint = previous?.clickCheckpoint ?? {through: firstDay, count: 0};
  if (!Number.isSafeInteger(checkpoint.through) || checkpoint.through < firstDay || checkpoint.through > end ||
      checkpoint.through % day !== 0 || !Number.isSafeInteger(checkpoint.count) || checkpoint.count < 0) {
    throw new Error('Invalid cumulative click checkpoint');
  }

  const retentionStart = new Date(end);
  const date = retentionStart.getUTCDate();
  retentionStart.setUTCDate(1);
  retentionStart.setUTCMonth(retentionStart.getUTCMonth() - 6);
  const lastDay = new Date(Date.UTC(retentionStart.getUTCFullYear(), retentionStart.getUTCMonth() + 1, 0)).getUTCDate();
  retentionStart.setUTCDate(Math.min(date, lastDay));
  if (checkpoint.through < retentionStart.getTime()) {
    throw new Error('Click checkpoint is older than the Umami retention window');
  }

  // Keep yesterday's and today's clicks open so recent reporting delays can settle.
  const through = Math.max(checkpoint.through, Math.floor(end / day) * day - day);
  const metricsPath = '/websites/' + website + '/metrics?';
  const metricsLimit = 1000;

  async function metrics(type, eventType, startAt, endAt) {
    if (endAt < startAt) return [];
    const query = new URLSearchParams({
      startAt: String(startAt),
      endAt: String(endAt),
      type,
      eventType: String(eventType),
      limit: String(metricsLimit),
    });
    const body = await get(metricsPath + query, auth);
    const rows = body.data ?? body;
    if (!Array.isArray(rows)) throw new Error('Unexpected metrics response');
    if (rows.length >= metricsLimit) {
      if (startAt === endAt) throw new Error('Metrics report was truncated');
      const mid = startAt + Math.floor((endAt - startAt) / 2);
      const left = await metrics(type, eventType, startAt, mid);
      return left.concat(await metrics(type, eventType, mid + 1, endAt));
    }
    if (rows.some(row => typeof row.x !== 'string' || !Number.isSafeInteger(row.y) || row.y < 0)) {
      throw new Error('Invalid metric row');
    }
    return rows;
  }

  async function clicksBetween(startAt, endAt) {
    if (endAt < startAt) return 0;
    const events = await metrics('event', 2, startAt, endAt);
    return events.filter(row => row.x.endsWith('_click')).reduce((sum, row) => sum + row.y, 0);
  }

  const known = new Set(articles);
  const articleEvents = ['home_article_click', 'article_link_click', 'search_result_click'];

  async function addPageviews(reads, startAt, endAt) {
    const rows = await metrics('path', 1, startAt, endAt);
    let views = 0;
    for (const {x: path, y: count} of rows) {
      views += count;
      if (known.has(path) && count > 0) reads[path] = (reads[path] ?? 0) + count;
    }
    return views;
  }

  async function collectPageviews() {
    const saved = previous?.pageviewCheckpoint ?? {through: firstDay, views: 0, reads: {}};
    if (!Number.isSafeInteger(saved.through) || saved.through < firstDay || saved.through < retentionStart.getTime() ||
        saved.through > end || saved.through % day !== 0 || !Number.isSafeInteger(saved.views) || saved.views < 0 ||
        !saved.reads || Array.isArray(saved.reads) || typeof saved.reads !== 'object' ||
        Object.values(saved.reads).some(count => !Number.isSafeInteger(count) || count < 0)) {
      throw new Error('Invalid cumulative pageview checkpoint');
    }
    const pageviewThrough = Math.max(saved.through, through);
    const archivedReads = {...saved.reads};
    const archivedViews = saved.views + await addPageviews(archivedReads, saved.through, pageviewThrough - 1);
    const reads = {...archivedReads};
    const views = archivedViews + await addPageviews(reads, pageviewThrough, end);
    return {views, reads, pageviewCheckpoint: {through: pageviewThrough, views: archivedViews, reads: archivedReads}};
  }

  async function addArticleClicks(counts, event, startAt, endAt) {
    if (endAt < startAt) return;
    const query = new URLSearchParams({event, eventName: event, propertyName: 'destination', startAt, endAt});
    const body = await get('/websites/' + website + '/event-data/values?' + query, auth);
    const rows = body.data ?? body;
    if (!Array.isArray(rows) || rows.some(row => typeof row.value !== 'string' || !Number.isSafeInteger(row.total) || row.total < 0)) {
      throw new Error('Invalid article click breakdown');
    }
    // This endpoint returns at most 100 destination values per interval.
    if (rows.length >= 100) {
      if (startAt === endAt) throw new Error('Article click breakdown is incomplete');
      const mid = startAt + Math.floor((endAt - startAt) / 2);
      await addArticleClicks(counts, event, startAt, mid);
      await addArticleClicks(counts, event, mid + 1, endAt);
      return;
    }
    for (const {value, total} of rows) {
      if (known.has(value) && total > 0) counts[value] = (counts[value] ?? 0) + total;
    }
  }

  async function collectArticleClicks() {
    const saved = previous?.articleClickCheckpoint ?? {through: firstDay, counts: {}};
    if (!Number.isSafeInteger(saved.through) || saved.through < firstDay || saved.through < retentionStart.getTime() ||
        saved.through > end || saved.through % day !== 0 || !saved.counts || Array.isArray(saved.counts) ||
        typeof saved.counts !== 'object' || Object.values(saved.counts).some(count => !Number.isSafeInteger(count) || count < 0)) {
      throw new Error('Invalid article click checkpoint');
    }
    const articleThrough = Math.max(saved.through, through);
    const counts = Object.fromEntries(Object.entries(saved.counts).filter(([path]) => known.has(path)));
    await Promise.all(articleEvents.map(event => addArticleClicks(counts, event, saved.through, articleThrough - 1)));
    const articleClicks = {...counts};
    await Promise.all(articleEvents.map(event => addArticleClicks(articleClicks, event, articleThrough, end)));
    return {articleClickCheckpoint: {through: articleThrough, counts}, articleClicks};
  }

  // Umami's metric range is inclusive at both ends. Advance at a UTC midnight.
  const [pageviews, archived, recent, articleStats] = await Promise.all([
    collectPageviews(),
    clicksBetween(checkpoint.through, through - 1),
    clicksBetween(through, end),
    collectArticleClicks().catch(error => ({articleClickError: error.message})),
  ]);
  const count = checkpoint.count + archived;
  return {version: 2, updatedAt: new Date(end).toISOString(), clicks: count + recent, clickCheckpoint: {through, count}, ...pageviews, ...articleStats};
}
