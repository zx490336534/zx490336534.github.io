import subprocess as s,sys,json,math,re,os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
story=json.loads(Path(sys.argv[1]).read_text()); root=Path(sys.argv[2]);root.mkdir(parents=True,exist_ok=True);fps=int(os.getenv("VIDEO_FPS","24"))
def render(rec):
 i,j,t=rec
 a=root/f'{i}-{j}.aiff';m=root/f'{i}-{j}.mp3'
 if not m.exists():
  s.run(['say','-v','Tingting','-r','172','-o',str(a),t],check=True)
  s.run(['ffmpeg','-v','error','-y','-i',str(a),'-af','highpass=f=70,volume=1.20','-ar','48000','-ac','1','-b:a','72k',str(m)],check=True)
  a.unlink()
 d=float(s.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(m)]))
 assert d>0.3
 return i,j,t,d,m.name
def phrases(t):
 return [a.strip() for a in re.split(r'(?<=[。！？])',t) if a.strip()]
rows=[(i,j,t) for i,x in enumerate(story['scenes']) for j,t in enumerate(phrases(x['voice']))]
slides=[{k:v for k,v in scene.items() if k!='voice'}|{'cues':[],'duration':0} for scene in story['scenes']]
with ThreadPoolExecutor(max_workers=3) as ex:
 for i,j,t,d,file in ex.map(render,rows):
  x=slides[i];f=x['duration']+8 if not x['cues'] else x['duration']+2
  end=f+math.ceil(d*fps)
  x['cues'].append({'from':f,'to':end,'text':t,'file':file});x['duration']=end
for x in slides:x['duration']+=17
(root.parent/'pilot-props.json').write_text(json.dumps({k:v for k,v in story.items() if k!='scenes'}|{'slides':slides},ensure_ascii=False))
def stamp(frame):
 n=round(frame*1000/fps)
 return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02}.{n%1000:03}'
lines=['WEBVTT',''];pos=int(os.getenv('VIDEO_OPEN_FRAMES','0'))
for slide in slides:
 for cue in slide['cues']:lines.extend([f'{stamp(pos+cue["from"])} --> {stamp(pos+cue["to"])}',cue['text'],''])
 pos+=slide['duration']
if story.get('slug'):(root.parent/(story['slug']+'.vtt')).write_text('\n'.join(lines)+'\n')
print('Seconds:',sum(x['duration'] for x in slides)/fps)
