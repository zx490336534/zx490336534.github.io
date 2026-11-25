import { enablePassageComments } from './passage-comments.js';

const comments = document.querySelector('.article-comments');
const canonical = new URL(document.querySelector('link[rel="canonical"]').href);
const origin = 'https://giscus.app';
const systemDark = matchMedia('(prefers-color-scheme: dark)');
let widgetType;
let articleWidget;

function currentTheme() {
  const selected = document.documentElement.dataset.theme;
  const dark = selected === 'dark' || (!selected && systemDark.matches);
  return canonical.origin + '/css/giscus-' + (dark ? 'dark' : 'light') + '.css';
}

function getWidgetType() {
  widgetType ??= import('/lib/giscus-widget/widget.js').then(() => {
    const GiscusWidget = customElements.get('giscus-widget');
    class ScopedGiscus extends GiscusWidget {
      handleMessageEvent(event) {
        if (event.source === this.iframeRef?.contentWindow && event.data?.giscus) super.handleMessageEvent(event);
      }

      getMetaContent(name, preferOpenGraph) {
        if (name === 'description' && this.dataset.excerpt) return this.dataset.excerpt;
        if (name === 'giscus:backlink' && this.dataset.backlink) return this.dataset.backlink;
        return super.getMetaContent(name, preferOpenGraph);
      }
    }
    customElements.define('blog-giscus', ScopedGiscus);
  }).catch(error => {
    widgetType = undefined;
    throw error;
  });
  return widgetType;
}

async function mountDiscussion(mount, options, stillCurrent = () => true) {
  await getWidgetType();
  if (!stillCurrent()) return null;
  const widget = document.createElement('blog-giscus');
  const config = {
    id: options.id,
    repo: comments.dataset.repo,
    repoid: comments.dataset.repoId,
    category: comments.dataset.category,
    categoryid: comments.dataset.categoryId,
    mapping: 'specific',
    term: options.term,
    strict: '1',
    reactionsenabled: options.isPassage ? '0' : '1',
    emitmetadata: options.isPassage ? '0' : '1',
    inputposition: options.isPassage ? 'top' : 'bottom',
    theme: currentTheme(),
    lang: 'zh-CN',
    loading: options.loading,
  };
  for (const [key, value] of Object.entries(config)) widget.setAttribute(key, value);
  if (options.excerpt) widget.dataset.excerpt = options.excerpt;
  if (options.backlink) widget.dataset.backlink = options.backlink;
  mount.replaceChildren(widget);
  await widget.updateComplete;
  return widget;
}

function refreshTheme() {
  for (const widget of document.querySelectorAll('blog-giscus')) widget.setAttribute('theme', currentTheme());
}

const articleStatus = comments.querySelector(':scope > [role="status"]');
const articleRetry = comments.querySelector('[data-retry-comments]');
const articleGuide = comments.querySelector('[data-comment-guide]');

async function loadArticleComments() {
  articleRetry.hidden = true;
  articleStatus.textContent = '正在加载评论…';
  try {
    articleWidget = await mountDiscussion(comments.querySelector('.giscus'), {
      id: 'article-discussion',
      term: comments.dataset.articlePath,
      loading: location.hash === '#comments' || location.hash === '#article-discussion' ||
        new URLSearchParams(location.search).has('giscus') ? 'eager' : 'lazy',
    });
    articleStatus.textContent = '';
  } catch {
    articleStatus.textContent = '评论暂时加载失败，请重试。';
    articleRetry.hidden = false;
  }
}

articleRetry.addEventListener('click', loadArticleComments);
window.addEventListener('message', event => {
  if (event.origin !== origin || event.source !== articleWidget?.iframeRef?.contentWindow) return;
  const count = event.data?.giscus?.discussion?.totalCommentCount;
  if (Number.isSafeInteger(count)) articleGuide.hidden = count < 1;
});
systemDark.addEventListener('change', refreshTheme);
new MutationObserver(refreshTheme).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});

enablePassageComments(mountDiscussion, canonical);
loadArticleComments();
