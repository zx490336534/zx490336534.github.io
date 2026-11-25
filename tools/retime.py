"""Recreate narration, timeline and captions from one editable storyboard on macOS."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
catalog_path = root / 'episodes.json'
catalog = json.loads(catalog_path.read_text())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode', choices=catalog)
    parser.add_argument('--apply', action='store_true',
                        help='replace generated audio, timeline and captions')
    a = parser.parse_args()
    if not a.apply:
        parser.error('请先备份现有配音。确认替换后加 --apply。')
    if sys.platform != 'darwin':
        raise SystemExit('重新合成配音需 macOS 的 Tingting 语音；已归档的配音可在其他平台直接重渲。')
    project = root / 'episodes' / a.episode
    spec = project / 'storyboard.json'
    data = json.loads(spec.read_text())
    meta = catalog[a.episode]
    cover = bool(data.get('cover'))
    intro = project / 'assets' / 'establish.webp'
    if data['slug'] != a.episode or (cover and not intro.is_file()):
        raise SystemExit('请检查 storyboard.json 的文章 ID 和片头插画。')
    script = 'second_audio.py' if meta['renderer'] in {'animated', 'newest'} else 'pilot_audio.py'
    env = os.environ | {'VIDEO_FPS': str(meta['fps']), 'VIDEO_OPEN_FRAMES': '48' if cover else '0'}
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        subprocess.run([sys.executable, str(root/'tools'/script), str(spec), str(tmp/'audio')], env=env, check=True)
        timeline = json.loads((tmp/'pilot-props.json').read_text())
        for p in (project/'assets').glob('*.mp3'):
            p.unlink()
        for p in (tmp/'audio').glob('*.mp3'):
            shutil.copyfile(p, project/'assets'/p.name)
        shutil.copyfile(tmp/'pilot-props.json', project/'timeline.json')
        shutil.copyfile(tmp/(a.episode+'.vtt'), project/'captions.vtt')
        if not cover:
            intro.unlink(missing_ok=True)
    meta['frameCount'] = sum(s['duration'] for s in timeline['slides']) + (48 if cover else 0)
    meta['title'] = data['title']
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False)+'\n')
    subprocess.run([sys.executable, str(root/'tools/render.py'), '--check'], check=True)
    print('配音、字幕与时间轴已更新；未发布任何内容。')

if __name__ == '__main__':
    main()
