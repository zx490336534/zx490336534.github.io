'use strict';
(() => {
  const video = document.querySelector('.watch-page video');
  if (!video) return;
  const offset = (value) => /^\d{1,5}$/.test(value ?? '') ? Number(value) : null;
  function seek(seconds) {
    const apply = () => {
      if (Number.isFinite(video.duration) && seconds < video.duration) video.currentTime = seconds;
    };
    if (video.readyState > 0) apply();
    else video.addEventListener('loadedmetadata', apply, {once: true});
  }
  function seekURL() {
    const value = offset(new URL(location.href).searchParams.get('t'));
    if (value !== null) seek(value);
  }
  seekURL();
  addEventListener('popstate', seekURL);
  document.querySelectorAll('[data-watch-offset]').forEach((link) => {
    link.addEventListener('click', (event) => {
      if (event.button || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
      const value = offset(link.dataset.watchOffset);
      if (value === null) return;
      event.preventDefault();
      history.pushState(null, '', link.href);
      seek(value);
      video.scrollIntoView({block: 'center'});
    });
  });
})();
