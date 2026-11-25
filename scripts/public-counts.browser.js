async ({api, slug, website, articles}) => {
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
  const end = Date.now();
  const metricsPath = '/websites/' + website + '/metrics?';

  async function metrics(type, eventType) {
    const query = new URLSearchParams({
      startAt: String(end - days * 86400000),
      endAt: String(end),
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

  const [paths, events] = await Promise.all([metrics('path', 1), metrics('event', 2)]);
  const known = new Set(articles);
  const reads = {};
  for (const row of paths) {
    if (known.has(row.x)) reads[row.x] = (reads[row.x] ?? 0) + row.y;
  }
  const clicks = events.filter(row => row.x.endsWith('_click')).reduce((sum, row) => sum + row.y, 0);
  return {days, updatedAt: new Date(end).toISOString(), clicks, reads};
}
