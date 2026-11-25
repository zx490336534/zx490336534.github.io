"""Regenerate an episode's narration/timing using Microsoft Edge Xiaoxiao only."""
import argparse, asyncio, hashlib, json, math, re, shutil, subprocess, sys, tempfile
from pathlib import Path

from synth_xiaoxiao import batch, VOICE

root = Path(__file__).resolve().parents[1]
catalog = root/'episodes.json'

def dump(path, payload):
    pending=path.with_suffix(path.suffix+'.tmp')
    pending.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    pending.replace(path)

def main():
    index=json.loads(catalog.read_text())
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('episode',choices=index)
    a.add_argument('--apply',action='store_true')
    a.add_argument('--rate',default='+0%')
    a.add_argument('--workers',type=int,choices=[1,2,3],default=2)
    opt=a.parse_args()
    if not opt.apply: a.error('Voice generation sends the edited narration text to Edge TTS; confirm with --apply.')
    project=root/'episodes'/opt.episode
    story=json.loads((project/'storyboard.json').read_text())
    old=json.loads((project/'timeline.json').read_text())
    assert story['slug']==old['slug']==opt.episode
    meta=index[opt.episode]; fps=meta['fps']
    cover=bool(story.get('cover'))
    intro=project/'assets/establish.webp'
    assert not cover or intro.is_file(), 'Missing approved cover art'
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        slides=[]; requests=[]
        for i,scene in enumerate(story['scenes']):
            previous=old['slides'][i] if i<len(old['slides']) else {}
            slide={k:v for k,v in previous.items() if k not in {'cues','duration','artAsset'}}
            slide.update({k:v for k,v in scene.items() if k!='voice'})
            art=slide.get('artAsset')
            if art is not None:
                assert meta['renderer']=='illustrated' and re.fullmatch(r'scene-[0-9]{2}\.webp',art)
                assert (project/'assets'/art).is_file(), f'Missing approved art {art}'
            text=[s.strip() for s in re.split(r'(?<=[。！？])',scene['voice']) if s.strip()]
            if not text: raise ValueError('Every scene requires nonempty narration.')
            cues=[dict(text=s,file=f'{i}-{j}.mp3') for j,s in enumerate(text)]
            requests.extend(dict(text=c['text'],output=str(tmp/c['file']),rate=opt.rate) for c in cues)
            slides.append(slide|{'cues':cues})
        info=asyncio.run(batch(requests,opt.workers))
        evidence={Path(req['output']).name:result for req,result in zip(requests,info)}
        captions=['WEBVTT',''];absolute=48 if cover else 0
        def stamp(frame):
            ms=round(frame*1000/fps)
            return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
        for slide in slides:
            cursor=0
            for i,cue in enumerate(slide['cues']):
                c=evidence[cue['file']]
                sound=tmp/cue['file']
                assert c['voice']==VOICE and c['audioSHA256']==hashlib.sha256(sound.read_bytes()).hexdigest()
                at=cursor+(round(.5*fps) if not i else max(2,round(.12*fps)))
                end=at+math.ceil(c['durationSeconds']*fps)
                cue.update({'from':at,'to':end})
                captions.extend([f'{stamp(absolute+at)} --> {stamp(absolute+end)}',cue['text'],''])
                cursor=end
            slide['duration']=cursor+round(1.05*fps);absolute+=slide['duration']
        output={k:v for k,v in story.items() if k!='scenes'}|{'slides':slides}
        for file in evidence:
            shutil.copyfile(tmp/file,project/'assets'/file)
        for f in (project/'assets').glob('*.mp3'):
            if f.name not in evidence:f.unlink()
        if not cover:intro.unlink(missing_ok=True)
        dump(project/'timeline.json',output)
        (project/'captions.vtt').write_text('\n'.join(captions).rstrip()+'\n',encoding='utf8')
        dump(project/'voice-evidence.json',dict(voice=VOICE,provider='Microsoft Edge TTS',
             fps=fps,frameCount=absolute,cueCount=len(evidence),segments=evidence))
        meta.update(frameCount=absolute,title=story['title'],voice=VOICE,voiceProvider='Microsoft Edge TTS')
        dump(catalog,index)
    subprocess.run([sys.executable,str(root/'tools/render.py'),'--check'],check=True)
    print('已重建晓晓配音、字幕和时间轴；未发布。')

if __name__=='__main__': main()
