'use strict';

(() => {
  const website = document.currentScript?.dataset.websiteId;
  const host = location.hostname;
  const siteHosts = new Set(['www.zhongxin.website', 'zhongxin.website']);
  if (!website || !siteHosts.has(host) || navigator.doNotTrack === '1' || navigator.globalPrivacyControl === true) return;

  function pagePath(path) {
    return path.replace(/\/index\.html$/, '/');
  }

  const canonical = document.querySelector('link[rel="canonical"]');
  const path = pagePath(canonical ? new URL(canonical.href).pathname : location.pathname);
  const title = path === '/tools/test-cases/' ? '测试用例脑图生成器' : document.title;
  const from = document.referrer ? new URL(document.referrer) : null;
  const referrer = from && !siteHosts.has(from.hostname) && /^https?:$/.test(from.protocol) ? from.origin : '';
  const endpoint = 'https://gateway.umami.is/api/send';

  // Only publish navigational metadata. The tool's inputs and browser storage stay local.
  function track(name, destination) {
    const payload = {website, hostname: host, url: path, title, referrer};
    if (name) payload.name = name;
    if (destination) payload.data = {destination};
    fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type: 'event', payload}),
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
      keepalive: true,
    }).catch(() => {});
  }

  function clickName(link, destination) {
    if (destination.startsWith('/article/')) {
      if (link.closest('#search-results')) return 'search_result_click';
      if (link.matches('.front-story')) return 'home_article_click';
      return 'article_link_click';
    }
    if (destination.startsWith('/categories/')) return 'category_click';
    if (destination.startsWith('/tags/')) return 'tag_click';
    if (destination.startsWith('/tools/test-cases/')) return 'tool_entry_click';
    if (destination.startsWith('/teaching-aihom/') || destination.startsWith('/teaching-kuai/')) return 'course_link_click';
    if (['/', '/lab/', '/archives/', '/about/', '/atom.xml'].includes(destination)) return 'navigation_click';
    return '';
  }

  function trackClick(event) {
    if (event.defaultPrevented || event.type === 'auxclick' && event.button !== 1) return;
    const link = event.target instanceof Element ? event.target.closest('a[href]') : null;
    if (!link) return;
    const url = new URL(link.href, location.href);
    if (!/^https?:$/.test(url.protocol)) return;
    if (link.matches('.source-link') && url.hostname === 'mp.weixin.qq.com') {
      track('wechat_source_click');
      return;
    }
    if (!siteHosts.has(url.hostname)) return;
    const destination = pagePath(url.pathname);
    if (destination === path) return;
    const name = clickName(link, destination);
    if (name) track(name, destination);
  }

  track();
  document.addEventListener('click', trackClick);
  document.addEventListener('auxclick', trackClick);
})();
