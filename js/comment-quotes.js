'use strict';

(() => {
  const body = document.querySelector('#article-text');
  const action = document.querySelector('[data-quote-action]');
  const draft = document.querySelector('[data-comment-quote]');
  if (!body || !action || !draft) return;

  const preview = draft.querySelector('[data-comment-quote-text]');
  const manual = draft.querySelector('[data-comment-quote-copy]');
  const status = draft.querySelector('[data-comment-quote-status]');
  const copy = draft.querySelector('[data-copy-comment-quote]');
  const source = draft.querySelector('[data-comment-quote-source]');
  const clear = draft.querySelector('[data-clear-comment-quote]');
  const blocks = 'p, li, dt, dd, h1, h2, h3, h4, h5, h6, pre, td, th, figcaption, blockquote, div';
  const normalize = text => text.replace(/\s+/gu, ' ').trim();
  const encode = text => encodeURIComponent(text).replace(/-/g, '%2D');
  let selection;
  let scheduled = false;
  let markdown = '';

  function selectedRange() {
    const current = document.getSelection();
    if (!current || current.isCollapsed || current.rangeCount !== 1) return null;
    const range = current.getRangeAt(0).cloneRange();
    if (!body.contains(range.startContainer)) return null;
    if (!body.contains(range.endContainer)) {
      if (range.comparePoint(body, body.childNodes.length) !== 0) return null;
      const original = normalize(range.toString());
      range.setEnd(body, body.childNodes.length);
      if (normalize(range.toString()) !== original) return null;
    }
    const quote = current.toString().trim();
    return normalize(quote) ? {range, quote} : null;
  }

  function blockFor(node) {
    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    return element.closest(blocks) || body;
  }

  function locationFor({range, quote}) {
    let anchor = body.id;
    for (const heading of body.querySelectorAll('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]')) {
      if (range.comparePoint(heading, 0) > 0) break;
      anchor = heading.id;
    }

    const startBlock = blockFor(range.startContainer);
    const endBlock = blockFor(range.endContainer);
    const before = range.cloneRange();
    before.setStart(startBlock, 0);
    before.setEnd(range.startContainer, range.startOffset);
    const after = range.cloneRange();
    after.setStart(range.endContainer, range.endOffset);
    after.setEnd(endBlock, endBlock.childNodes.length);
    const prefix = Array.from(normalize(before.toString())).slice(-48).join('');
    const suffix = Array.from(normalize(after.toString())).slice(0, 48).join('');

    const text = normalize(quote);
    const sameBlock = startBlock === endBlock && !/\n\s*\n/.test(quote);
    let terms = [text];
    if (!sameBlock || Array.from(text).length > 140) {
      const first = range.cloneRange();
      const last = range.cloneRange();
      if (startBlock !== endBlock) {
        first.setEnd(startBlock, startBlock.childNodes.length);
        last.setStart(endBlock, 0);
      }
      terms = [
        Array.from(normalize(first.toString())).slice(0, 44).join('').trimEnd(),
        Array.from(normalize(last.toString())).slice(-44).join('').trimStart(),
      ].filter(Boolean);
    }
    const directive = [prefix && encode(prefix) + '-', ...terms.map(encode), suffix && '-' + encode(suffix)].filter(Boolean).join(',');
    const canonical = document.querySelector('link[rel="canonical"]').href;
    return canonical + '#' + encodeURIComponent(anchor) + ':~:text=' + directive;
  }

  function updateAction() {
    scheduled = false;
    selection = selectedRange();
    const rect = selection && [...selection.range.getClientRects()].find(box => box.bottom > 0 && box.top < innerHeight && box.width > 0);
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

  async function copyDraft() {
    const text = markdown;
    try {
      await navigator.clipboard.writeText(text);
      if (text !== markdown) return;
      manual.hidden = true;
      preview.hidden = false;
      status.textContent = '已复制引用和原文链接。将它们粘贴到下方评论框，再写下你的留言。';
      copy.focus({preventScroll: true});
    } catch {
      if (text !== markdown) return;
      manual.value = text;
      manual.hidden = false;
      preview.hidden = true;
      status.textContent = '请手动复制引用和链接，再粘贴到评论框。';
      manual.focus({preventScroll: true});
      manual.select();
    }
  }

  action.addEventListener('pointerdown', event => event.preventDefault());
  action.addEventListener('click', () => {
    if (!selection) return;
    const position = locationFor(selection);
    const excerpt = selection.quote;
    const quoted = excerpt.split(/\r?\n/u).map(line => '> ' + line.replace(/[\\`*_\[\]~<>]/g, '\\$&')).join('\n');
    markdown = quoted + '\n\n[查看原文位置](<' + position + '>)\n\n';
    preview.textContent = excerpt;
    source.href = position;
    draft.hidden = false;
    document.getSelection().removeAllRanges();
    action.hidden = true;
    draft.scrollIntoView({block: 'start'});
    copyDraft();
  });
  copy.addEventListener('click', copyDraft);
  clear.addEventListener('click', () => {
    markdown = '';
    draft.hidden = true;
    const heading = document.querySelector('#comments-title');
    heading.tabIndex = -1;
    heading.focus({preventScroll: true});
  });
  document.addEventListener('selectionchange', scheduleAction);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !action.hidden) {
      document.getSelection().removeAllRanges();
      action.hidden = true;
    }
  });
  window.addEventListener('scroll', scheduleAction, {passive: true});
  window.addEventListener('resize', scheduleAction);
})();
