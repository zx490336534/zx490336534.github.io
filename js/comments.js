'use strict';

(() => {
  const comments = document.querySelector('.article-comments');
  if (!comments) return;

  const button = comments.querySelector('button[data-open-comments]');
  const status = comments.querySelector('[role="status"]');
  const mount = comments.querySelector('.giscus');
  const origin = 'https://giscus.app';
  let requested = false;

  function theme() {
    const selected = document.documentElement.dataset.theme;
    return selected === 'light' || selected === 'dark' ? selected : 'preferred_color_scheme';
  }

  function updateTheme() {
    mount.querySelector('iframe.giscus-frame')?.contentWindow?.postMessage({
      giscus: {setConfig: {theme: theme()}},
    }, origin);
  }

  function load() {
    if (requested) return;
    requested = true;
    button.disabled = true;
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
      emitMetadata: '0',
      inputPosition: 'bottom',
      theme: theme(),
      lang: 'zh-CN',
    });
    script.addEventListener('load', () => {
      status.textContent = '';
      button.hidden = true;
      updateTheme();
    }, {once: true});
    script.addEventListener('error', () => {
      requested = false;
      button.disabled = false;
      status.textContent = '评论暂时加载失败，可以重试或前往 GitHub 讨论区。';
      script.remove();
    }, {once: true});
    mount.append(script);
  }

  button.addEventListener('click', load);
  document.querySelector('[data-jump-comments]')?.addEventListener('click', load);
  new MutationObserver(updateTheme).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  });

  // Giscus returns to this page after authorizing a reader on GitHub.
  if (location.hash === '#comments' || new URLSearchParams(location.search).has('giscus')) load();
})();
