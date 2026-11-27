'use strict';
(() => {
  const directory = document.querySelector('[data-video-library]');
  if (directory) {
    const filter = directory.querySelector('.vc-filter');
    const input = filter.querySelector('input');
    const clear = filter.querySelector('button');
    const feedback = filter.querySelector('[role="status"]');
    const cards = directory.querySelector('.vc-shelves');
    const featured = directory.querySelector('.vc-hero');
    const menu = directory.querySelector('.vc-library-tools nav');
    const standalone = directory.querySelector('.vc-standalone');
    const index = directory.querySelector('.vc-index');
    const rows = [...index.querySelectorAll('li')].map(row => ({
      row, text: normalize(row.dataset.episodeTitle + ' ' + row.dataset.episodeGroup)
    }));
    for (const link of index.querySelectorAll('[data-player-url]')) {
      link.href = link.dataset.playerUrl;
    }
    let openBeforeSearch = false;
    let searching = false;

    function normalize(value) {
      return value.normalize('NFKC').toLocaleLowerCase();
    }
    function filterEpisodes() {
      const query = normalize(input.value.trim());
      const active = Boolean(query);
      const words = query.split(/\s+/u);
      if (active && !searching) openBeforeSearch = index.open;
      if (active) index.open = true;
      if (!active && searching) index.open = openBeforeSearch;
      for (const node of [cards, featured, menu, standalone]) node.hidden = active;
      let count = 0;
      for (const item of rows) {
        item.row.hidden = active && !words.every(token => item.text.includes(token));
        if (!item.row.hidden) count++;
      }
      index.hidden = active && !count;
      clear.hidden = !input.value;
      feedback.textContent = active ? (count ? '找到 ' + count + ' 支视频' : '没有匹配的视频，请换个关键词。') : '';
      searching = active;
    }
    filter.hidden = false;
    input.addEventListener('input', event => { if (!event.isComposing) filterEpisodes(); });
    input.addEventListener('compositionend', filterEpisodes);
    clear.addEventListener('click', () => { input.value = ''; filterEpisodes(); input.focus(); });
    window.addEventListener('pageshow', () => requestAnimationFrame(filterEpisodes));
    filterEpisodes();
  }

  const playlist = document.querySelector('[data-playlist]');
  if (!playlist) return;
  const video = playlist.querySelector('video');
  const source = video.querySelector('source');
  const track = video.querySelector('track');
  const entries = [...playlist.querySelectorAll('[data-player-episode]')];
  const transcript = playlist.querySelector('[data-player-transcript]');
  const link = playlist.querySelector('[data-player-article]');
  const currentName = playlist.querySelector('#vp-now');
  const currentPosition = playlist.querySelector('[data-position]');
  const status = playlist.querySelector('[data-player-status]');
  const controls = playlist.querySelector('[data-controls]');
  const autoplay = playlist.querySelector('[data-autonext]');
  const previous = playlist.querySelector('[data-previous]');
  const next = playlist.querySelector('[data-next]');
  const retry = playlist.querySelector('[data-retry]');
  const queue = playlist.querySelector('.vp-queue-scroll');
  const key = 'blog-video-auto-next';
  let current = -1;
  let playRequest = 0;

  function episodeFromLocation() {
    const slug = new URL(window.location.href).searchParams.get('episode');
    return Math.max(0, entries.findIndex(entry => entry.dataset.playerEpisode === slug));
  }
  function episodeLocation(entry) {
    const url = new URL(window.location.href);
    url.searchParams.set('episode', entry.dataset.playerEpisode);
    return url;
  }
  function updateCaption(text, canRetry = false) {
    status.textContent = text;
    retry.hidden = !canRetry;
  }
  function startPlayback() {
    const requested = ++playRequest;
    const promise = video.play();
    if (promise) promise.catch(error => {
      if (requested !== playRequest || error.name === 'AbortError') return;
      updateCaption(error.name === 'NotAllowedError'
        ? '已切到下一集，浏览器需要你点一下才能继续播放。'
        : '此视频暂时无法播放，可重试或打开原文播放器。', true);
    });
  }
  function pick(index, play, historyMode) {
    const entry = entries[index];
    if (!entry) return;
    const data = entry.dataset;
    if (current >= 0 && current !== index) entries[current].removeAttribute('aria-current');
    entry.setAttribute('aria-current', 'true');
    currentName.textContent = data.title;
    currentPosition.textContent = '正在观看 · 第 ' + (index + 1) + ' / ' + entries.length + ' 集';
    link.href = data.article;
    transcript.href = data.fallback;
    transcript.textContent = new URL(data.fallback).pathname.startsWith('/videos/watch/')
      ? '分章文字稿 ↗' : '打开原文播放器 ↗';
    previous.disabled = index < 1;
    next.disabled = index + 1 >= entries.length;
    if (index !== current) {
      const captionsMode = track.track.mode;
      ++playRequest;
      video.pause();
      video.poster = data.poster;
      if (source.getAttribute('src') !== data.src) {
        source.src = data.src;
        track.src = data.captions;
        track.track.mode = captionsMode;
        video.load();
      }
      // Scroll only the independently scrollable queue, never the viewing page.
      const top = entry.getBoundingClientRect().top - queue.getBoundingClientRect().top + queue.scrollTop;
      if (queue.scrollHeight > queue.clientHeight && (top < queue.scrollTop || top + entry.offsetHeight > queue.scrollTop + queue.clientHeight)) {
        queue.scrollTop = Math.max(0, top - 12);
      }
    }
    current = index;
    if (historyMode) {
      const url = episodeLocation(entry);
      if (url.href !== location.href) history[historyMode + 'State'](null, '', url);
    }
    updateCaption('');
    if (play) startPlayback();
  }
  try { autoplay.checked = localStorage.getItem(key) !== 'off'; } catch {}
  autoplay.addEventListener('change', () => {
    try { localStorage.setItem(key, autoplay.checked ? 'on' : 'off'); } catch {}
  });
  previous.addEventListener('click', () => pick(current - 1, true, 'push'));
  next.addEventListener('click', () => pick(current + 1, true, 'push'));
  retry.addEventListener('click', () => { if (video.error || video.networkState === 3) video.load(); startPlayback(); });
  entries.forEach((entry, index) => {
    // Keep static article links useful even without JavaScript; once enhanced,
    // modifiers and copying a link share the same player and the selected episode.
    const fallbackUrl = entry.href;
    entry.dataset.fallback = fallbackUrl;
    entry.href = episodeLocation(entry).href;
    entry.addEventListener('click', event => {
      if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      pick(index, true, 'push');
    });
  });
  window.addEventListener('popstate', () => pick(episodeFromLocation(), false, ''));
  video.addEventListener('playing', () => updateCaption(''));
  video.addEventListener('ended', () => {
    if (current + 1 === entries.length) {
      updateCaption('本系列已播放完毕。');
    } else if (autoplay.checked) {
      pick(current + 1, true, 'replace');
    } else {
      updateCaption('本集已播放完毕。');
    }
  });
  source.addEventListener('error', () => updateCaption('此视频暂时无法播放，可重试或打开原文播放器。', true));
  controls.hidden = false;
  pick(episodeFromLocation(), false, '');
})();
