from pathlib import Path
import subprocess as sp, json, csv, re, zipfile, sys
root=Path.cwd(); raw=root/'raw'; public=root/'final'; public.mkdir(exist_ok=True)
frames=json.loads((raw/'frames.json').read_text()); ev=json.loads((raw/'evidence.json').read_text())
assert 50 <= len(frames) and ev['fixtureModel'] and ev['appUnmodified'] and ev['modelCalls']>=1 and ev['mcpRead'] and ev['skillIncluded']
edited=ev['editedTitle']
with next((raw/'downloads').glob('*.csv')).open(encoding='utf-8-sig',newline='') as fp: rows=list(csv.DictReader(fp))
assert len(rows)==3 and any(r['测试名称'].endswith(edited) for r in rows)
with zipfile.ZipFile(next((raw/'downloads').glob('*.xmind'))) as f:
 content=json.loads(f.read('content.json'))
 assert edited in json.dumps(content,ensure_ascii=False)
def ts(v):
 ms=round(v*1000); sec,ms=divmod(ms,1000); m,s=divmod(sec,60);h,m=divmod(m,60)
 return f'{h:02}:{m:02}:{s:02}.{ms:03}'
base=frames[0]['at']; length=125.10
flat=[(0.,'@cover')]
for f in frames:
 t=f['at']-base
 if t<6.12 or t-flat[-1][0] < 0.013: continue
 if t>length-0.04: break
 flat.append((t,f['name']))
sp.run(['ffmpeg','-v','error','-y','-i','cover.jpg','-vf','scale=1440:900:flags=lanczos','-frames:v','1','-q:v','2','-update','1','cover-frame.jpg'],check=True)
with open('frames.ffconcat','w') as f:
 f.write('ffconcat version 1.0\n')
 for i,(ts0,p) in enumerate(flat):
  dur=(flat[i+1][0] if i+1<len(flat) else length)-ts0
  loc='cover-frame.jpg' if p=='@cover' else f'raw/{p}'
  f.write(f"file '{loc}'\noption framerate 1000\nduration {max(0.013,dur):.4f}\n")
 f.write(f"file 'raw/{flat[-1][1]}'\noption framerate 1000\n")
inputs=[];filters=[]; cues=['WEBVTT','']; durations=[]
speech=(root/'voice.tsv').read_text().splitlines()
for i,line in enumerate(speech):
 stamp,word=line.split('\t',1); stamp=float(stamp); p=f'voice-{i+1}.mp3'; inputs.extend(['-i',p])
 d=float(sp.check_output(['ffprobe','-v','error','-select_streams','a:0','-show_entries','format=duration','-of','csv=p=0',p],text=True))
 available=(float(speech[i+1].split('\t',1)[0]) if i+1<len(speech) else length)-stamp-0.27
 tempo=max(1,d/available)
 assert d>2 and tempo<=1.20,(i,d,tempo)
 d=d/tempo
 durations.append((stamp,stamp+d)); filters.append(f'[{i+1}:a]aresample=48000,atempo={tempo:.5f},adelay={round(stamp*1000)}:all=1[a{i+1}]')
 wrap=re.split(r'(?<=[。？！；])',word,maxsplit=1)
 caption='\n'.join(w.strip() for w in wrap if w.strip())
 cues.extend([f'{ts(stamp)} --> {ts(stamp+d)}',caption,''])
assert all(b+0.08<c for (_,b),(c,_) in zip(durations,durations[1:])),durations
# Retain original recording pixels; variable compositor updates re-timed to 30 fps.
filters.append(''.join(f'[a{i+1}]' for i in range(len(inputs)//2))+f'amix=inputs={len(inputs)//2}:normalize=0,loudnorm=I=-17:TP=-1.3:LRA=8,apad[voice]')
path=public/'ai-test-cases-demo-v2.mp4'
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i','frames.ffconcat',*inputs,'-filter_complex',';'.join(filters),'-map','0:v:0','-map','[voice]','-vf','fps=30,scale=1440:900:flags=lanczos,setsar=1','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','110k','-movflags','+faststart','-t',str(length),str(path)]
sp.run(cmd,check=True)
(public/'ai-test-cases-demo-v2.zh-CN.vtt').write_text('\n'.join(cues).rstrip()+'\n')
sp.run(['cwebp','-quiet','-resize','1440','900','-q','86','cover.png','-o',str(public/'ai-test-cases-demo-v2.webp')],check=True)
sp.run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],check=True)
print(json.dumps({'files':[f.name for f in public.iterdir()],'real_recording_frames':len(frames),'exact_csv_rows':len(rows),'xmind_contains_edit':True,'cues':durations},ensure_ascii=False))
