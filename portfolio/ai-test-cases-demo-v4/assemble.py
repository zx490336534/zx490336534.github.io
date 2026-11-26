from pathlib import Path
import json, re, sys, subprocess as sp, shutil
old=Path(sys.argv[1]); assert old.is_dir()
out=Path('final');out.mkdir(exist_ok=True)
ev=json.loads(Path('raw/evidence.json').read_text())
assert ev['verifiedHandoff'] and ev['run']['status']=='passed' and ev['browser']['clicks']==2 and ev['browser']['total']==1
stem='ai-test-cases-demo-v4'
def run(a):sp.run(a,check=True)
def duration(f):return float(sp.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(f)],text=True))
def ts(x):
 v=round(x*1000); sec,ms=divmod(v,1000); h,r=divmod(sec,3600); m,s=divmod(r,60)
 return f'{h:02}:{m:02}:{s:02}.{ms:03}'
oldmp4=old/'ai-test-cases-demo-v3.mp4'
platform=old/'ai-test-cases-demo-v3.zh-CN.vtt'
offset=duration(oldmp4)
cues=[platform.read_text().rstrip()]
chapters={};frames=['ffconcat version 1.0'];args=[];audio=[]
t=0
for i,line in enumerate(Path('voice.tsv').read_text().splitlines(),1):
 n,caption=line.split('\t',1); assert int(n)==i
 voice=f'raw/voice-{i}.mp3'; dur=duration(voice); assert 3<dur<30
 args.extend(['-i',voice]);chapters[str(i)]=round(offset+t,3)
 audio.append(f'[{i}:a]aresample=48000,afade=t=in:d=0.025,adelay={round((t+.60)*1000)}:all=1[a{i}]')
 length=round(dur+2,2)
 if i==6:
  timings=[('6-before',2.1),('6-first',1.55),('6',length-3.65)]
 else:timings=[(str(i),length)]
 for label,dt in timings:
  frames+=["file 'raw/frame-"+label+".png'","duration "+str(dt)]
 parts=re.split(r'(?<=[，。；：])',caption)
 if len(caption)>46 and len(parts)>2:
  split=min(range(1,len(parts)),key=lambda k:abs(len(''.join(parts[:k]))-len(caption)/2))
  caption=''.join(parts[:split]).strip()+'\n'+''.join(parts[split:]).strip()
 cues.append(ts(offset+t+.6)+' --> '+ts(offset+t+.6+dur)+'\n'+caption)
 t+=length
frames+=["file 'raw/frame-7.png'"]
Path('frames.ffconcat').write_text('\n'.join(frames)+'\n')
af=';'.join(audio+[''.join(f'[a{i}]' for i in range(1,8))+'amix=inputs=7:normalize=0,loudnorm=I=-17:TP=-1.3:LRA=8,aresample=48000,apad[voice]'])
run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i','frames.ffconcat',*args,'-filter_complex',af,'-map','0:v','-map','[voice]','-vf','fps=30,format=yuv420p,setsar=1','-c:v','libx264','-preset','veryfast','-crf','19','-c:a','aac','-b:a','112k','-ar','48000','-t',str(t),'raw/plugin.mp4'])
f='[0:v]fps=30,scale=1440:900:flags=lanczos,format=yuv420p,setsar=1[a];[1:v]fps=30,format=yuv420p,setsar=1[b];[0:a]aresample=48000[c];[1:a]aresample=48000[d];[a][c][b][d]concat=n=2:v=1:a=1[v][s]'
mp4=out/(stem+'.mp4')
run(['ffmpeg','-v','error','-y','-i',str(oldmp4),'-i','raw/plugin.mp4','-filter_complex',f,'-map','[v]','-map','[s]','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','112k','-movflags','+faststart',str(mp4)])
assert abs(duration(mp4)-offset-t)<.3
(out/(stem+'.zh-CN.vtt')).write_text('\n\n'.join(cues)+'\n')
shutil.copyfile(old/'ai-test-cases-demo-v3.webp',out/(stem+'.webp'))
(out/'chapters.json').write_text(json.dumps({'duration':duration(mp4),'chapters':chapters,'voiceProvider':'Microsoft Edge TTS','voice':'zh-CN-XiaoxiaoNeural'},indent=2))
run(['ffmpeg','-v','error','-xerror','-i',str(mp4),'-f','null','-'])
print((out/'chapters.json').read_text())
