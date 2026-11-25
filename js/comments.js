'use strict';

(() => {
  const comments = document.querySelector('.article-comments');
  if (!comments) return;

  const retry = comments.querySelector('[data-retry-comments], [data-open-comments]');
  const guide = comments.querySelector('[data-comment-guide]');
  const status = comments.querySelector(':scope > [role="status"]');
  const mount = comments.querySelector('.giscus');
  const origin = 'https://giscus.app';
  const blog = new URL(document.querySelector('link[rel="canonical"]').href).origin;
  const systemDark = matchMedia('(prefers-color-scheme: dark)');
  let requested = false;

  function theme() {
    const selected = document.documentElement.dataset.theme;
    const dark = selected === 'dark' || (!selected && systemDark.matches);
    return blog + '/css/giscus-' + (dark ? 'dark' : 'light') + '.css';
  }

  function updateTheme() {
    mount.querySelector('iframe.giscus-frame')?.contentWindow?.postMessage({
      giscus: {setConfig: {theme: theme()}},
    }, origin);
  }

  function showCommentGuide(event) {
    const frame = mount.querySelector('iframe.giscus-frame');
    if (!guide || !frame || event.origin !== origin || event.source !== frame.contentWindow) return;
    const count = event.data?.giscus?.discussion?.totalCommentCount;
    if (Number.isSafeInteger(count)) guide.hidden = count < 1;
  }

  function load() {
    if (requested) return;
    requested = true;
    retry.hidden = true;
    status.textContent = '正在加载评论…';

    const script = document.createElement('script');
    script.src = origin + '/client.js';
    script.crossOrigin = 'anonymous';
    script.async = true;
    Object.assign(script.dataset, {
      repo: comments.dataset.repo,
      repoId: comments.dataset.repoId,
      category: comments.dataset.category,
      categoryId: comments.dataset.categoryId,
      mapping: 'specific',
      term: comments.dataset.articlePath,
      strict: '1',
      reactionsEnabled: '1',
      emitMetadata: guide ? '1' : '0',
      inputPosition: 'bottom',
      theme: theme(),
      lang: 'zh-CN',
      loading: location.hash === '#comments' || new URLSearchParams(location.search).has('giscus') ? 'eager' : 'lazy',
    });
    script.addEventListener('load', () => {
      status.textContent = '';
      mount.querySelector('iframe.giscus-frame')?.addEventListener('load', updateTheme, {once: true});
      updateTheme();
    }, {once: true});
    script.addEventListener('error', () => {
      requested = false;
      retry.hidden = false;
      status.textContent = '评论暂时加载失败，请重试。';
      script.remove();
    }, {once: true});
    mount.append(script);
  }

  retry.addEventListener('click', load);
  window.addEventListener('message', showCommentGuide);
  systemDark.addEventListener('change', updateTheme);
  new MutationObserver(updateTheme).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  });

  load();
})();
