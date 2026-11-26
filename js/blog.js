'use strict';

const dialog = document.querySelector('#search-dialog');
const search = document.querySelector('#article-search');
const results = document.querySelector('#search-results');
const status = document.querySelector('#search-status');
let index;

function enableScrollNavigation() {
  const masthead = document.querySelector('.masthead');
  if (!masthead) return;
  const root = document.documentElement;
  const position = () => Math.max(0, Math.min(scrollY, root.scrollHeight - root.clientHeight));
  let previous = position();
  let height = masthead.offsetHeight;
  let distance = 0;
  let visible;
  let pending = false;

  function setOffset() {
    root.style.setProperty('--masthead-offset', visible ? height + 'px' : '0px');
  }

  function show(next) {
    if (visible === next) return;
    visible = next;
    masthead.toggleAttribute('data-scroll-hidden', !visible);
    setOffset();
  }

  function update() {
    pending = false;
    const y = position();
    const delta = y - previous;
    previous = y;
    const focused = document.activeElement;
    if (y <= height || (masthead.contains(focused) && focused.matches(':focus-visible'))) {
      distance = 0;
      show(true);
      return;
    }
    if (!delta) return;
    if (distance * delta < 0) distance = 0;
    distance += delta;
    if ((visible && distance >= 28) || (!visible && distance <= -14)) {
      show(!visible);
      distance = 0;
    }
  }

  masthead.setAttribute('data-scroll-nav', '');
  root.style.setProperty('--masthead-height', height + 'px');
  show(previous <= height || masthead.contains(document.activeElement));
  addEventListener('scroll', () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(update);
  }, {passive: true});
  masthead.addEventListener('focusin', () => {
    previous = position();
    distance = 0;
    show(true);
  });

  function measure() {
    const next = masthead.offsetHeight;
    if (next === height) return;
    height = next;
    root.style.setProperty('--masthead-height', height + 'px');
    setOffset();
    update();
  }

  if ('ResizeObserver' in window) new ResizeObserver(measure).observe(masthead);
  else addEventListener('resize', measure);
}

enableScrollNavigation();

if (matchMedia('(max-width: 760px)').matches) {
  document.querySelector('.outline details')?.removeAttribute('open');
  document.querySelector('.catalog-menu[data-compact]')?.removeAttribute('open');
}

function entries() {
  index ??= fetch('/search.json').then(response => {
    if (!response.ok) throw new Error('Search index failed to load');
    return response.json();
  }).then(posts => posts.map(post => ({
    ...post,
    titleKey: normalize(post.title),
    heading: normalize([post.title, ...post.topics].join(' ')),
    content: normalize(post.text),
  }))).catch(error => {
    index = undefined;
    throw error;
  });
  return index;
}

function normalize(text) {
  return text.normalize('NFKC').toLocaleLowerCase();
}

function openSearch() {
  if (!dialog.open) dialog.showModal();
}

document.querySelectorAll('[data-open-search]').forEach(button => button.addEventListener('click', openSearch));
document.addEventListener('keydown', event => {
  if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k' || event.isComposing) return;
  event.preventDefault();
  openSearch();
});

function score(post, query, words) {
  if (post.titleKey.includes(query)) return 4;
  if (words.every(word => post.titleKey.includes(word))) return 3;
  if (words.every(word => post.heading.includes(word))) return 2;
  return words.every(word => post.heading.includes(word) || post.content.includes(word)) ? 1 : 0;
}

function snippet(post, words, rank) {
  if (rank > 1) return post.summary ?? '';
  const text = post.text.toLocaleLowerCase();
  const offsets = words.map(word => text.indexOf(word)).filter(offset => offset >= 0);
  if (!offsets.length) return post.summary ?? post.text.slice(0, 115);
  const start = Math.max(0, Math.min(...offsets) - 28);
  return (start ? '…' : '') + post.text.slice(start, start + 115) + (start + 115 < post.text.length ? '…' : '');
}

let version = 0;
async function showResults() {
  const current = ++version;
  const query = normalize(search.value.trim());
  results.replaceChildren();
  status.textContent = query ? '正在搜索…' : '';
  if (!query) return;

  let posts;
  try {
    posts = await entries();
  } catch {
    if (current === version) status.textContent = '无法加载搜索，稍后可重试。';
    return;
  }
  if (current !== version) return;

  const words = query.split(/\s+/);
  const matches = posts.map(post => ({post, rank:score(post, query, words)}))
    .filter(match => match.rank)
    .sort((a, b) => b.rank - a.rank);
  status.textContent = matches.length ? '找到 ' + matches.length + ' 篇文章' : '没有找到相关文章';
  for (const {post, rank} of matches.slice(0, 20)) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = post.path;
    const title = document.createElement('strong');
    title.textContent = post.title;
    const meta = document.createElement('span');
    meta.className = 'search-result-meta';
    const date = document.createElement('time');
    date.dateTime = post.date;
    date.textContent = post.date;
    meta.append(date, post.topics[0] ? ' · ' + post.topics[0] : '');
    const summary = document.createElement('p');
    summary.textContent = snippet(post, words, rank);
    const copy = document.createElement('span');
    copy.append(title, meta, summary);
    if (post.cover?.startsWith('/images/')) {
      const picture = document.createElement('img');
      picture.className = 'post-thumbnail';
      picture.src = post.cover;
      picture.alt = '';
      picture.width = 180;
      picture.height = 90;
      picture.loading = 'lazy';
      picture.decoding = 'async';
      link.className = 'search-result-cover';
      link.append(picture);
    }
    link.append(copy);
    item.append(link);
    results.append(item);
  }
}
search.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || event.isComposing || !search.value) return;
  // Chromium clears a populated search field before sending a dialog close request.
  event.preventDefault();
  dialog.close();
});
search.addEventListener('input', event => { if (!event.isComposing) showResults(); });
search.addEventListener('compositionend', showResults);

const library = document.querySelector('[data-tag-library]');
if (library) {
  const input = library.querySelector('[data-tag-filter]');
  const counter = library.querySelector('[data-tag-status]');
  const more = library.querySelector('details');
  const tags = [...library.querySelectorAll('.taxonomy li')];
  input.closest('label').hidden = false;
  input.addEventListener('input', () => {
    const term = normalize(input.value.trim());
    let count = 0;
    let expand = false;
    for (const tag of tags) {
      const matched = normalize(tag.querySelector('a').firstChild.textContent).includes(term);
      tag.hidden = !matched;
      if (matched) count += 1;
      if (matched && more?.contains(tag)) expand = true;
    }
    if (more) more.open = Boolean(term && expand);
    counter.textContent = term ? '找到 ' + count + ' 个标签' : '';
  });
}

const codeLanguageNames = {
  bash: 'Bash', sh: 'Shell', shell: 'Shell', zsh: 'Zsh',
  py: 'Python', python: 'Python', js: 'JavaScript', javascript: 'JavaScript',
  ts: 'TypeScript', typescript: 'TypeScript', java: 'Java', groovy: 'Groovy',
  ruby: 'Ruby', rust: 'Rust', go: 'Go', swift: 'Swift', dockerfile: 'Dockerfile',
};

function codeLanguage(block, highlight) {
  const classes = [...block.classList, ...(block.querySelector('code')?.classList ?? [])];
  const explicit = classes.find(name => /^(?:language-|lang-)[\w+.-]+$/i.test(name));
  const legacy = [...(highlight?.classList ?? [])].find(name => name !== 'highlight');
  const language = (explicit?.replace(/^(?:language-|lang-)/i, '') ?? legacy ?? '').toLowerCase();
  if (!language || /^(?:plain|plaintext|text|nohighlight)$/.test(language)) return '代码';
  return Object.hasOwn(codeLanguageNames, language) ? codeLanguageNames[language] : language.toUpperCase();
}

function codeText(block) {
  const lines = block.querySelectorAll('.line');
  if (lines.length) return [...lines].map(line => line.textContent).join('\n');
  const clone = block.cloneNode(true);
  clone.querySelectorAll('.linenum').forEach(number => number.remove());
  clone.querySelectorAll('br').forEach(br => br.replaceWith('\n'));
  const numbered = clone.querySelector('ol.linenums');
  return numbered ? [...numbered.children].map(line => line.textContent).join('\n') : clone.textContent;
}

const codePanels = new Set();
const codeWrapControls = new WeakMap();
function updateCodeWrap(scroll) {
  const controls = codeWrapControls.get(scroll);
  if (!controls) return;
  const { panel, button } = controls;
  const wrapped = panel.classList.contains('is-wrapped');
  const overflows = scroll.clientWidth > 0 && scroll.scrollWidth > scroll.clientWidth + 1;
  button.hidden = scroll.hidden || (!wrapped && !overflows);
}
const codeResize = typeof ResizeObserver === 'function' ? new ResizeObserver(entries => {
  for (const { target } of entries) updateCodeWrap(target);
}) : null;
function refreshCodeWrap() {
  for (const scroll of document.querySelectorAll('.code-scroll')) updateCodeWrap(scroll);
}
let codeControlId = 0;
for (const block of document.querySelectorAll('.post-body pre')) {
  const highlight = block.closest('figure.highlight');
  const target = highlight ?? block;
  if ((highlight && block.closest('.gutter')) || codePanels.has(target)) continue;
  codePanels.add(target);

  const panel = document.createElement('div');
  panel.className = 'code-panel';
  const tools = document.createElement('div');
  tools.className = 'code-tools';
  const language = document.createElement('span');
  language.className = 'code-language';
  language.textContent = codeLanguage(block, highlight);
  tools.append(language);
  const actions = document.createElement('div');
  actions.className = 'code-actions';
  const wrap = document.createElement('button');
  wrap.type = 'button';
  wrap.textContent = '自动换行';
  wrap.setAttribute('aria-pressed', 'false');
  wrap.hidden = true;
  actions.append(wrap);
  tools.append(actions);

  if (navigator.clipboard?.writeText) {
    const copy = document.createElement('button');
    copy.type = 'button';
    copy.textContent = '复制代码';
    const feedback = document.createElement('span');
    feedback.className = 'visually-hidden';
    feedback.setAttribute('role', 'status');
    let reset;
    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(codeText(block));
        copy.textContent = '已复制';
        feedback.textContent = '代码已复制';
      } catch {
        copy.textContent = '复制失败';
        feedback.textContent = '复制失败，可选中代码手动复制';
      }
      clearTimeout(reset);
      reset = setTimeout(() => {
        copy.textContent = '复制代码';
        feedback.textContent = '';
      }, 2000);
    });
    actions.append(copy, feedback);
  }

  const scroll = document.createElement('div');
  scroll.className = 'code-scroll';
  do { scroll.id = 'article-code-block-' + (++codeControlId); }
  while (document.getElementById(scroll.id));
  scroll.tabIndex = 0;
  scroll.setAttribute('role', 'region');
  scroll.setAttribute('aria-label', language.textContent === '代码' ? '代码' : language.textContent + ' 代码');
  for (const number of target.querySelectorAll('.gutter, span.linenum')) number.setAttribute('aria-hidden', 'true');
  target.before(panel);
  scroll.append(target);
  panel.append(tools, scroll);
  const fold = document.createElement('button');
  fold.type = 'button';
  fold.className = 'code-fold';
  fold.textContent = '折叠代码';
  fold.setAttribute('aria-controls', scroll.id);
  fold.setAttribute('aria-expanded', 'true');
  actions.prepend(fold);
  function setCodeCollapsed(collapsed) {
    scroll.hidden = collapsed;
    fold.setAttribute('aria-expanded', String(!collapsed));
    fold.textContent = collapsed ? '展开代码' : '折叠代码';
    panel.classList.toggle('is-collapsed', collapsed);
    updateCodeWrap(scroll);
    if (!collapsed) requestAnimationFrame(() => updateCodeWrap(scroll));
  }
  fold.addEventListener('click', () => setCodeCollapsed(!scroll.hidden));
  codeWrapControls.set(scroll, { panel, button: wrap, setCodeCollapsed });
  wrap.addEventListener('click', () => {
    const wrapped = panel.classList.toggle('is-wrapped');
    wrap.setAttribute('aria-pressed', String(wrapped));
    scroll.scrollLeft = 0;
    // Keep focus when restoring horizontal layout after a viewport resize.
    if (wrapped || scroll.scrollWidth > scroll.clientWidth + 1) updateCodeWrap(scroll);
    else wrap.addEventListener('blur', () => updateCodeWrap(scroll), { once: true });
  });
  codeResize?.observe(scroll);
}
if (codePanels.size) {
  window.addEventListener('hashchange', () => {
    let anchor;
    try { anchor = document.getElementById(decodeURIComponent(location.hash.slice(1))); }
    catch { return; }
    const scroll = anchor?.closest('.code-scroll');
    if (!scroll?.hidden) return;
    codeWrapControls.get(scroll)?.setCodeCollapsed(false);
    requestAnimationFrame(() => anchor.scrollIntoView({ block: 'start' }));
  });
  window.addEventListener('load', refreshCodeWrap, { once: true });
  document.fonts?.ready.then(refreshCodeWrap);
  if (!codeResize) {
    window.addEventListener('resize', refreshCodeWrap);
    document.addEventListener('toggle', refreshCodeWrap, true);
  }
}
