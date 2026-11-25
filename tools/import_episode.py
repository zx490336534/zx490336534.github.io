"""Import one reviewed episode from explicit, already sanitized production inputs."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

root = Path(__file__).resolve().parents[1]
risk_patterns = {
    'full phone number': r'(?<!\d)1[3-9]\d{9}(?!\d)',
    'local or private URL': r'https?://(?:localhost\b|127\.|10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.)',
    'private path': r'(?:/Users/|/home/)[A-Za-z0-9_-]{3,}/',
    'credential-shaped string': r'(?:sk-[a-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{12,}|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}|-----BEGIN [A-Z ]+PRIVATE KEY|\bBearer\s+[A-Za-z0-9_.-]{12,})',
}


def screen(text, label):
    for reason, pattern in risk_patterns.items():
        if re.search(pattern, text, re.I):
            raise ValueError(f'{label}: {reason}; replace with a synthetic placeholder before import')


def asset_name(name):
    return re.fullmatch(r'[0-9]+-[0-9]+\.mp3', name) is not None


def regular_file(p):
    if p.is_symlink() or not p.is_file() or not p.stat().st_size:
        raise ValueError(f'Expected a nonempty regular file: {p.name}')
    return p


def get_text(p, label):
    text = regular_file(p).read_text(encoding='utf-8')
    screen(text, label)
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--storyboard', required=True, type=Path)
    p.add_argument('--timeline', required=True, type=Path)
    p.add_argument('--assets', required=True, type=Path)
    p.add_argument('--captions', required=True, type=Path)
    p.add_argument('--check-only', action='store_true', help='validate without writing any files')
    p.add_argument('--reviewed', action='store_true',
                   help='confirm visual, narration and text were checked for placeholders')
    a = p.parse_args()
    if not a.check_only and not a.reviewed:
        p.error('inspect all media for original sensitive values before confirming --reviewed')
    if a.assets.is_symlink() or not a.assets.is_dir():
        p.error('--assets must be a regular directory')
    story = json.loads(get_text(a.storyboard, 'storyboard'))
    data = json.loads(get_text(a.timeline, 'timeline'))
    vtt = get_text(a.captions, 'captions')
    slug = story['slug']
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,95}', slug) or slug != data['slug']:
        p.error('storyboard and timeline must use the same valid article ID')
    if not vtt.startswith('WEBVTT\n') or len(story['scenes']) != len(data['slides']):
        p.error('captions must be VTT and storyboard/timeline scene counts must match')
    cue_files = set()
    narration = []
    for scene in data['slides']:
        at = 0
        for cue in scene['cues']:
            name = cue['file']
            if not asset_name(name) or name in cue_files:
                p.error('audio names must have the scene-sentence.mp3 format and be unique')
            if not at <= cue['from'] < cue['to'] <= scene['duration']:
                p.error('invalid narration cue interval')
            at = cue['to']
            cue_files.add(name)
            narration.append(cue['text'])
    if ['\n'.join(block.splitlines()[1:]) for block in vtt.strip().split('\n\n')[1:]] != narration:
        p.error('timeline and VTT cue text do not match')
    if data.get('cover'):
        cue_files.add('establish.webp')
    for f in sorted(cue_files):
        regular_file(a.assets/f)
    if a.check_only:
        print(f'{slug}: validated exact media allowlist ({len(cue_files)} files)')
        return
    d = root/'episodes'/slug
    catalog_path = root/'episodes.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    if d.exists() or slug in catalog:
        p.error('episode already exists; update its reviewed files in place rather than overwriting them')
    with tempfile.TemporaryDirectory(prefix='.import-', dir=d.parent) as temp:
        w = Path(temp)
        one = w/slug
        (one/'assets').mkdir(parents=True)
        for f, content in [('storyboard.json', story), ('timeline.json', data)]:
            (one/f).write_text(json.dumps(content, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        (one/'captions.vtt').write_text(vtt.rstrip()+'\n', encoding='utf-8')
        for f in sorted(cue_files):
            shutil.copyfile(a.assets/f, one/'assets'/f)
        catalog[slug] = {'renderer': 'animated', 'fps': 16, 'title': story['title'],
                         'frameCount': sum(s['duration'] for s in data['slides']) + 48*bool(data.get('cover'))}
        new_index = w/'episodes.json'
        new_index.write_text(json.dumps(catalog, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        one.rename(d)
        new_index.replace(catalog_path)
    print(f'{slug}: archived {len(cue_files)} reviewed source assets; nothing uploaded')


if __name__ == '__main__':
    main()
