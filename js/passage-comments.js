const prefix = '#passage-discussion-';
const normalize = text => text.replace(/\s+/gu, ' ').trim();

export function enablePassageComments(mountDiscussion, canonical) {
  const body = document.querySelector('#article-text');
  const action = document.querySelector('[data-quote-action]');
  const dialog = document.querySelector('#passage-comments');
  const preview = dialog.querySelector('[data-passage-excerpt]');
  const source = dialog.querySelector('[data-passage-source]');
  const mount = dialog.querySelector('[data-passage-widget]');
  const status = dialog.querySelector('[data-passage-status]');
  const retry = dialog.querySelector('[data-passage-retry]');
  let candidate;
  let pressed;
  let active;
  let scheduled = false;
  let previousHash = '';
  let attempt = 0;

  function selectionContext() {
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed || selection.rangeCount !== 1) return null;
    const range = selection.getRangeAt(0).cloneRange();
    if (!body.contains(range.startContainer)) return null;
    if (!body.contains(range.endContainer)) {
      if (range.comparePoint(body, body.childNodes.length) !== 0) return null;
      const text = normalize(range.toString());
      range.setEnd(body, body.childNodes.length);
      if (normalize(range.toString()) !== text) return null;
    }
    const start = range.startContainer;
    const element = start.nodeType === Node.ELEMENT_NODE ? start : start.parentElement;
    const block = element.closest('[data-passage-key]') ??
      [...body.querySelectorAll('[data-passage-key]')].find(item => range.intersectsNode(item));
    const excerpt = selection.toString().trim();
    return block && normalize(excerpt) ? {range, block, excerpt} : null;
  }

  function updateAction() {
    scheduled = false;
    if (pressed || dialog.open) return;
    candidate = selectionContext();
    const rect = candidate && [...candidate.range.getClientRects()].find(box => box.bottom > 0 && box.top < innerHeight && box.width > 0);
    action.hidden = !rect;
    if (!rect) return;
    const width = action.offsetWidth;
    const height = action.offsetHeight;
    const left = Math.max(8, Math.min(rect.left + rect.width / 2 - width / 2, innerWidth - width - 8));
    const top = rect.top > height + 12 ? rect.top - height - 8 : Math.min(rect.bottom + 8, innerHeight - height - 8);
    action.style.setProperty('--quote-left', left + 'px');
    action.style.setProperty('--quote-top', Math.max(8, top) + 'px');
  }

  function scheduleAction() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(updateAction);
  }

  function updateHash(hash) {
    const url = new URL(location.href);
    url.hash = hash;
    history.replaceState(history.state, '', url);
  }

  async function load(context) {
    const revision = ++attempt;
    retry.hidden = true;
    status.textContent = '正在加载这段的评论…';
    const needed = () => active === context && attempt === revision && dialog.open;
    try {
      const widget = await mountDiscussion(mount, {
        id: context.hash.slice(1),
        term: canonical.pathname + '#' + context.key,
        excerpt: Array.from(normalize(context.excerpt)).slice(0, 240).join(''),
        backlink: source.href,
        isPassage: true,
        loading: 'eager',
      }, needed);
      if (!widget || !needed()) return;
      if (location.hash !== context.hash) updateHash(context.hash);
      status.textContent = '';
    } catch {
      if (!needed()) return;
      status.textContent = '段落评论暂时加载失败，请重试。';
      retry.hidden = false;
    }
  }

  function open(block, excerpt) {
    const key = block.dataset.passageKey;
    const hash = prefix + key;
    const reuse = active?.key === key && mount.firstElementChild?.id === hash.slice(1);
    if (!dialog.open) previousHash = location.hash.startsWith(prefix) ? '#' + encodeURIComponent(block.id) : location.hash;
    active?.block.classList.remove('passage-current');
    active = {block, key, excerpt, hash};
    block.classList.add('passage-current');
    preview.textContent = excerpt;
    source.href = canonical.href + '#' + encodeURIComponent(block.id);
    updateHash(hash);
    action.hidden = true;
    document.getSelection()?.removeAllRanges();
    if (!dialog.open) dialog.showModal();
    if (reuse) {
      status.textContent = '';
      retry.hidden = true;
      return;
    }
    mount.replaceChildren();
    load(active);
  }

  function openBookmark() {
    if (!location.hash.startsWith(prefix)) return;
    const key = location.hash.slice(prefix.length);
    if (!/^[a-f0-9]{12}$/.test(key)) return;
    const block = body.querySelector('[data-passage-key="' + key + '"]');
    if (!block) return;
    block.scrollIntoView({block: 'center'});
    open(block, block.innerText.trim());
  }

  action.addEventListener('pointerdown', event => {
    pressed = candidate ?? selectionContext();
    if (pressed) event.preventDefault();
  });
  action.addEventListener('click', () => {
    const context = pressed ?? candidate ?? selectionContext();
    pressed = null;
    if (context) open(context.block, context.excerpt);
  });
  window.addEventListener('pointerup', () => {
    if (pressed) setTimeout(() => { pressed = null; scheduleAction(); }, 0);
  }, {passive: true});
  window.addEventListener('pointercancel', () => { pressed = null; scheduleAction(); });
  document.addEventListener('selectionchange', scheduleAction);
  document.addEventListener('keydown', event => {
    if (dialog.open) return;
    if (event.key === 'Escape' && !action.hidden) {
      document.getSelection()?.removeAllRanges();
      action.hidden = true;
    } else if (event.altKey && event.key === 'Enter') {
      const context = selectionContext();
      if (context) {
        event.preventDefault();
        open(context.block, context.excerpt);
      }
    }
  });
  retry.addEventListener('click', () => { if (active) load(active); });
  source.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    active?.block.classList.remove('passage-current');
    if (location.hash === active?.hash) updateHash(previousHash);
    if (document.activeElement === document.body && active) {
      active.block.tabIndex = -1;
      active.block.focus({preventScroll: true});
    }
    scheduleAction();
  });
  window.addEventListener('scroll', scheduleAction, {passive: true});
  window.addEventListener('resize', scheduleAction);
  window.addEventListener('hashchange', openBookmark);
  openBookmark();
}
