'use strict';

const dialog = document.querySelector('#search-dialog');
const search = document.querySelector('#article-search');
const results = document.querySelector('#search-results');
const status = document.querySelector('#search-status');
let index;

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

if (navigator.clipboard?.writeText) {
  for (const block of document.querySelectorAll('.post-body pre')) {
    const highlight = block.closest('figure.highlight');
    if (highlight && !block.closest('.code')) continue;
    const target = highlight ?? block;
    const tools = document.createElement('div');
    tools.className = 'code-tools';
    const copy = document.createElement('button');
    copy.type = 'button';
    copy.textContent = '复制代码';
    copy.setAttribute('aria-live', 'polite');
    copy.addEventListener('click', async () => {
      const lines = [...block.querySelectorAll('.line')];
      const text = lines.length ? lines.map(line => line.textContent).join('\n') : block.innerText;
      try {
        await navigator.clipboard.writeText(text);
        copy.textContent = '已复制';
      } catch {
        copy.textContent = '复制失败';
      }
      setTimeout(() => { copy.textContent = '复制代码'; }, 1600);
    });
    tools.append(copy);
    target.before(tools);
  }
}
