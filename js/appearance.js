'use strict';

(() => {
  const key = 'blog-appearance';
  const modes = ['system', 'light', 'dark'];
  const courseSheet = document.querySelector('#course-dark-theme');
  let mode = 'system';

  function apply(value) {
    if (value === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = value;
    if (courseSheet) {
      courseSheet.media = value === 'system' ? 'screen and (prefers-color-scheme: dark)'
        : value === 'dark' ? 'screen' : 'not all';
    }
  }

  function restore() {
    try {
      const saved = localStorage.getItem(key);
      mode = modes.includes(saved) ? saved : 'system';
    } catch {
      // Keep the current document's preference if storage is unavailable.
    }
    apply(mode);
    const select = document.querySelector('#site-appearance');
    if (select) select.value = mode;
  }
  restore();
  window.addEventListener('pageshow', event => { if (event.persisted) restore(); });
  window.addEventListener('storage', event => { if (event.key === key || event.key === null) restore(); });
  document.addEventListener('DOMContentLoaded', () => {
    const select = document.querySelector('#site-appearance');
    if (!select) return;
    select.value = mode;
    select.hidden = false;
    select.addEventListener('change', () => {
      mode = select.value;
      apply(mode);
      try {
        localStorage.setItem(key, mode);
      } catch {
        // The session can still use the selected appearance.
      }
    });
  });
})();
