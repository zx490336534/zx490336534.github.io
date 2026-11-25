#!/usr/bin/env python3
"""Synthesize only Edge Xiaoxiao using the Python edge-tts package. No fallback."""
import argparse, asyncio, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path
import edge_tts

VOICE = 'zh-CN-XiaoxiaoNeural'

def digest(data):
    return hashlib.sha256(data).hexdigest()

async def synth(text, output, rate):
    if not text.strip() or not re.fullmatch(r'[+-]\d{1,2}%', rate):
        raise ValueError('Expected nonempty text and an Edge relative rate like +0%.')
    output = Path(output)
    if output.suffix != '.mp3':
        raise ValueError('Expected MP3 output path')
    output.parent.mkdir(parents=True, exist_ok=True)
    sidecar = output.with_name(output.name+'.voice.json')
    expected = dict(provider='Microsoft Edge TTS', voice=VOICE, rate=rate,
                    textSHA256=digest(text.encode('utf8')))
    if output.is_file() and sidecar.is_file():
        old=json.loads(sidecar.read_text())
        if all(old.get(k)==v for k,v in expected.items()) and old.get('audioSHA256')==digest(output.read_bytes()):
            return old
    last=None
    for attempt in range(3):
        fd,name=tempfile.mkstemp(suffix='.mp3',prefix='.xiaoxiao-',dir=output.parent)
        os.close(fd)
        tmp=Path(name)
        try:
            await asyncio.wait_for(edge_tts.Communicate(text,voice=VOICE,rate=rate).save(str(tmp)),timeout=30)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name','-of','json',str(tmp)]))
            duration=float(probe['format']['duration'])
            if duration<.25 or probe['streams'][0]['codec_name']!='mp3': raise ValueError('Unexpected Edge audio output')
            info=expected|dict(audioSHA256=digest(tmp.read_bytes()),durationSeconds=duration,edgeTtsVersion=edge_tts.__version__)
            tmp.replace(output)
            side_tmp=sidecar.with_suffix('.tmp-'+str(os.getpid()))
            side_tmp.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
            side_tmp.replace(sidecar)
            return info
        except Exception as e:
            last=e
            if attempt<2: await asyncio.sleep(1.5*(attempt+1))
        finally: tmp.unlink(missing_ok=True)
    raise RuntimeError(f'Edge Xiaoxiao failed after three attempts: {type(last).__name__}: {last}')

async def batch(rows,workers):
    sem=asyncio.Semaphore(workers)
    async def one(row):
        async with sem: return await synth(row['text'],row['output'],row.get('rate','+0%'))
    outputs=[str(Path(r['output']).resolve()) for r in rows]
    if len(set(outputs))!=len(outputs): raise ValueError('Duplicate output path in a single batch')
    return await asyncio.gather(*(one(row) for row in rows))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    src=p.add_mutually_exclusive_group(required=True);src.add_argument('--text-file',type=Path);src.add_argument('--manifest',type=Path)
    p.add_argument('--output',type=Path);p.add_argument('--rate',default='+0%');p.add_argument('--workers',type=int,choices=[1,2,3],default=2)
    a=p.parse_args()
    if a.manifest:
        rows=json.loads(a.manifest.read_text(encoding='utf8'))
    else:
        if not a.output: p.error('--text-file requires --output')
        rows=[dict(text=a.text_file.read_text(encoding='utf8'),output=str(a.output),rate=a.rate)]
    verified=asyncio.run(batch(rows,a.workers))
    print(f'{len(verified)} Edge {VOICE} outputs verified')

if __name__=='__main__': main()
