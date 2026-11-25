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
    heading: [post.title, ...post.topics].join(' ').toLowerCase(),
    content: post.text.toLowerCase(),
  }))).catch(error => {
    index = undefined;
    throw error;
  });
  return index;
}

function openSearch() {
  if (!dialog.open) dialog.showModal();
}

document.querySelector('[data-open-search]').addEventListener('click', openSearch);
document.addEventListener('keydown', event => {
  if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k') return;
  event.preventDefault();
  openSearch();
});

let version = 0;
async function showResults() {
  const current = ++version;
  const query = search.value.toLowerCase().trim();
  results.replaceChildren();
  status.textContent = '';
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
  const titleMatches = [];
  const bodyMatches = [];
  for (const post of posts) {
    if (words.every(word => post.heading.includes(word))) titleMatches.push(post);
    else if (words.every(word => post.heading.includes(word) || post.content.includes(word))) bodyMatches.push(post);
  }
  const matches = [...titleMatches, ...bodyMatches];
  status.textContent = matches.length ? `找到 ${matches.length} 篇文章` : '没有找到相关的文章';
  for (const post of matches.slice(0, 20)) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = post.path;
    link.textContent = post.title;
    const date = document.createElement('time');
    date.dateTime = post.date;
    date.textContent = post.date;
    item.append(link, date);
    results.append(item);
  }
}
search.addEventListener('input', event => { if (!event.isComposing) showResults(); });
search.addEventListener('compositionend', showResults);
