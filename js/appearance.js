'use strict';

(() => {
  const key = 'blog-appearance';
  const modes = ['system', 'light', 'dark'];
  let mode = 'system';

  try {
    const saved = localStorage.getItem(key);
    if (modes.includes(saved)) mode = saved;
  } catch {
    // System appearance is also available when browser storage is disabled.
  }

  function apply(value) {
    if (value === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = value;
  }

  apply(mode);
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
