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
  const days = 30;
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

  async function metrics(type, eventType, startAt, endAt) {
    const query = new URLSearchParams({
      startAt: String(startAt),
      endAt: String(endAt),
      type,
      eventType: String(eventType),
      limit: '1000',
    });
    const body = await get(metricsPath + query, auth);
    const rows = body.data ?? body;
    if (!Array.isArray(rows)) throw new Error('Unexpected metrics response');
    if (rows.length >= 1000) throw new Error('Metrics report was truncated');
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

  // Umami's metric range is inclusive at both ends. Advance at a UTC midnight.
  const [paths, archived, recent] = await Promise.all([
    metrics('path', 1, end - days * day, end),
    clicksBetween(checkpoint.through, through - 1),
    clicksBetween(through, end),
  ]);
  const known = new Set(articles);
  const reads = {};
  for (const row of paths) {
    if (known.has(row.x)) reads[row.x] = (reads[row.x] ?? 0) + row.y;
  }
  const count = checkpoint.count + archived;
  return {days, updatedAt: new Date(end).toISOString(), clicks: count + recent, clickCheckpoint: {through, count}, reads};
}
