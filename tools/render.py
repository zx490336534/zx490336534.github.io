"""Render the checked-in project with existing assets; does not publish."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
catalog = json.loads((root / 'episodes.json').read_text(encoding='utf-8'))


def load(id):
    project = root / 'episodes' / id
    meta = catalog[id]
    data = json.loads((project / 'timeline.json').read_text(encoding='utf-8'))
    story = json.loads((project / 'storyboard.json').read_text(encoding='utf-8'))
    cover_frames = 48 if data.get('cover') else 0
    cues = set()
    narration = []
    assert id == data['slug'] == story['slug']
    assert len(data['slides']) == len(story['scenes'])
    for scene in data['slides']:
        pos = -1
        for cue in scene['cues']:
            name = cue['file']
            assert re.fullmatch(r'[0-9]+-[0-9]+\.mp3', name) and name not in cues
            cues.add(name)
            narration.append(cue["text"])
            assert pos <= cue['from'] < cue['to'] <= scene['duration'], id
            pos = cue['to']
    files = cues | ({'establish.webp'} if cover_frames else set())
    assert files == {x.name for x in (project / 'assets').iterdir()}, id
    assert all((project / 'assets' / f).stat().st_size > 0 for f in files), id
    vtt = (project / 'captions.vtt').read_text(encoding='utf-8')
    assert vtt.startswith('WEBVTT\n'), id
    assert ['\n'.join(block.splitlines()[1:]) for block in vtt.strip().split('\n\n')[1:]] == narration, id
    # frameCount in the inventory is historical; the editable timeline is authoritative.
    return project, meta, data


def find_browser(requested):
    if requested:
        return requested
    for name in ('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                 'google-chrome-stable', 'google-chrome', 'chromium', 'chromium-browser'):
        if executable := shutil.which(name):
            return executable
    raise SystemExit('请安装 Chrome 或通过 --browser 指定已有浏览器；本命令不会下载浏览器。')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('episode', nargs='?', choices=catalog)
    p.add_argument('--check', action='store_true', help='check all project manifests and assets')
    p.add_argument('--list', action='store_true', help='show available projects')
    p.add_argument('--frames', help='optional inclusive range such as 0-47 for draft preview')
    p.add_argument('--output', type=Path, help='write a local MP4, defaults to out/<slug>.mp4')
    p.add_argument('--browser', default=os.getenv('CHROME_BIN'))
    p.add_argument('--concurrency', type=int, default=4)
    a = p.parse_args()
    if a.list or a.check:
        for id, meta in catalog.items():
            if a.check:
                load(id)
            print(id, meta['title'])
        print(f'{len(catalog)} projects')
        return
    if not a.episode:
        p.error('choose an episode slug or pass --list')
    folder, meta, data = load(a.episode)
    kind = meta['renderer']
    data['variant'] = kind
    browser = find_browser(a.browser)
    out = (a.output or (root / 'out' / f'{a.episode}.mp4')).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    remotion = root / 'node_modules/.bin/remotion'
    if not remotion.is_file():
        raise SystemExit('请先在项目目录运行 npm ci。')
    entry = {'animated': 'EditionSecond.jsx', 'newest': 'EditionNewest.jsx'}.get(kind, 'Classic.jsx')
    composition = 'ArticleFilm' if kind == 'pilot' else 'EditorialArticle'
    with tempfile.TemporaryDirectory(prefix='blog-video-') as temp:
        props = Path(temp) / 'props.json'
        props.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        cmd = [str(remotion), 'render', str(root / 'renderers' / entry), composition, str(out),
               '--props', str(props), '--public-dir', str(folder / 'assets'),
               '--browser-executable', browser, '--codec=h264', '--crf=23',
               '--audio-bitrate=72k', '--x264-preset=fast', '--max-rate=1100k',
               '--buffer-size=2200k', f'--concurrency={a.concurrency}', '--log=warn']
        if a.frames:
            cmd.extend(['--frames', a.frames])
        subprocess.run(cmd, cwd=root, check=True)
    print(out)


if __name__ == '__main__':
    main()
