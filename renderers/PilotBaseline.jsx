import React from 'react';
import {AbsoluteFill,   Sequence, useCurrentFrame, interpolate, Easing, Audio, staticFile} from 'remotion';
const ink='#202a25', paper='#eceee4', forest='#294738', accent='#bf542d', muted='#677265', line='#aeb9a9';
const mono='Menlo, monospace', main='PingFang SC, Hiragino Sans GB, Arial, sans-serif';
const chapters=['反差','找瓶颈','看验证','过质量门','留证据','选自动化','做实验'];
const FX=(t,start=0,len=20)=>interpolate(t,[start,start+len],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.bezier(.2,.75,.23,1)});
const kicker=(s)=> <div style={{fontFamily:mono,fontSize:15,letterSpacing:3,textTransform:'uppercase',fontWeight:650,color:accent}}>{s}</div>;
const Live=({frame,at=0,children,style={}})=> {
 const p=FX(frame,at);return <div style={{opacity:p,transform:`translateY(${(1-p)*17}px)`,...style}}>{children}</div>;
}
export const Slide=({slide,index})=>{
 const frame=useCurrentFrame(), g=(at=0)=>FX(frame,at);
 const title={fontSize:61,fontWeight:800,lineHeight:1.1,letterSpacing:-2};
 const rule={height:1,background:line};
 const info={fontSize:18,color:muted};
 const pane={background:'#f7f7ef',outline:'1px solid #bcc7b7',borderRadius:18};
 const diagramStyle={position:'absolute',left:57,right:57,top:100,bottom:118};
 const text=(value)=> <span style={{fontWeight:700}}>{value}</span>;
 const label=(s,at=0)=> <Live frame={frame} at={at} style={{...title,color:ink}}>{s}</Live>;
 const cut=slide.cues.find((c)=>frame>=c.from&&frame<c.to);
 const at=(n,f=8)=>slide.cues[n]?.from||f;
 let body;
 if(index===0)body=<div style={{...diagramStyle,display:'flex',flexDirection:'column',alignItems:'flex-start',justifyContent:'center'}}>
  <Live frame={frame} at={2} style={{...title,fontSize:78}}>AI 写代码快了。</Live>
  <Live frame={frame} at={at(1,50)} style={{...title,fontSize:78,color:accent,marginTop:16}}>交付为什么还在等？</Live>
  <div style={{marginTop:33,width:'100%',display:'flex',alignItems:'center',gap:12}}>
  {['编码完成','测试环境','评审确认','发布'].map((s,i)=> <React.Fragment key={s}>{i>0?<div style={{height:1,background:line,flex:1}}/>:null}<Live frame={frame} at={35+i*13} style={{...pane,padding:'14px 24px',fontSize:22,fontWeight:700,color:i===0?forest:i===3?muted:accent}}>{s}<span style={{fontSize:13,marginLeft:13,color:muted}}>{i===0?'已完成':i===3?'待放行':'等待'}</span></Live></React.Fragment>)}
  </div>
  <div style={{fontSize:16,color:muted,marginTop:15,opacity:g(100)}}>示意案例，不代表团队实测</div>
 </div>;
 else if(index===1)body=<div style={diagramStyle}>{label('交付的四类时间')}
  <div style={{height:2,background:line,marginTop:24,marginBottom:25}}/>
  <div style={{display:'grid',gridTemplateColumns:'repeat(4, 1fr)',gap:14}}>
  {[['编码','写出可评审的改动'],['验证','核对测试与评审结果'],['等待','等环境、账号、决策'],['返工','修正偏差，重新验证']].map(([k,v],i)=><Live frame={frame} at={at(i+1,24+i*14)} key={k} style={{...pane,minHeight:182,padding:23,borderTop:`4px solid ${i===0?forest:accent}`}}><div style={{fontFamily:mono,fontSize:23,color:accent}}>0{i+1}</div><div style={{fontSize:38,fontWeight:750,margin:'15px 0'}}>{k}</div><div style={info}>{v}</div></Live>)}
  </div>
 </div>;
 else if(index===2)body=<div style={diagramStyle}>{label('三条测试通过，够了吗？')}
  <div style={{marginTop:35,display:'grid',gridTemplateColumns:'1fr 1fr',gap:28}}>
  <Live frame={frame} at={14} style={{...pane,padding:'23px 28px'}}>{kicker('RUN SUMMARY')}<div style={{fontSize:70,fontWeight:800,color:forest,marginTop:12}}>3 / 3</div><div style={info}>命令成功，不能单独作为放行证据</div></Live>
  <Live frame={frame} at={at(1,45)} style={{...pane,padding:'22px 29px',background:'#e3e9dc'}}>{kicker('EVIDENCE CHECK')}{['哪个版本？','覆盖了改动没？','断言检查的是业务结果吗？'].map((x,i)=><div key={x} style={{fontSize:23,padding:'12px 0',borderBottom:`1px solid ${line}`,opacity:g(56+i*24)}}><b style={{color:accent,marginRight:12}}>0{i+1}</b>{x}</div>)}</Live>
  </div>
 </div>;
 else if(index===3)body=<div style={{...diagramStyle,display:'flex',flexDirection:'column',justifyContent:'center',alignItems:'center'}}>{label('完成 ≠ 可信 ≠ 放行')}
  <div style={{display:'flex',gap:15,width:'100%',marginTop:34}}>
  {[['执行完成','工具跑完了'],['证据可信','输入、版本、结果可核对'],['允许放行','决定由有权限的人做']].map(([k,v],i)=><Live key={k} frame={frame} at={at(i,10+i*30)} style={{...pane,flex:1,padding:'25px 23px',textAlign:'center',background:i===2?'#dbe7d7':'#f7f7ef'}}><div style={{fontSize:35,fontWeight:780,marginBottom:16}}>{k}</div><div style={info}>{v}</div></Live>)}
  </div>
 </div>;
 else if(index===4)body=<div style={{...diagramStyle}}>{label('留下一张能接手的证据单')}
  <Live frame={frame} at={14} style={{...pane,padding:'17px 24px',marginTop:26,width:720,marginLeft:'auto',marginRight:'auto',boxShadow:'0 14px 0 #c2cdb8'}}>
    {['改动对应的版本','用来验证的用例','实际运行结果','未覆盖的范围'].map((x,i)=><div key={x} style={{padding:'11px 0',display:'flex',alignItems:'center',gap:23,fontSize:23,borderBottom:i===3?'none':`1px solid ${line}`,opacity:g(25+i*24)}}><span style={{fontFamily:mono,fontSize:16,color:accent}}>0{i+1}</span>{text(x)}<span style={{marginLeft:'auto',fontSize:16,color:muted}}>{i===3?'如实记录':'可核对'}</span></div>)}
  </Live>
 </div>;
 else if(index===5)body=<div style={diagramStyle}>{label('自动化用在反复发生的堵点')}
  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:20,marginTop:36}}>
  <Live frame={frame} at={at(0,20)} style={{...pane,padding:24,minHeight:154}}>{kicker('可重复')}<div style={{fontSize:36,fontWeight:720,margin:'18px 0'}}>固定检查</div><div style={info}>可自动执行，失败时留下证据</div></Live>
  <Live frame={frame} at={at(2,60)} style={{...pane,padding:24,minHeight:154,background:'#e0e8d9'}}>{kicker('需判断')}<div style={{fontSize:36,fontWeight:720,margin:'18px 0'}}>证据冲突</div><div style={info}>明确问题，交给人决定下一步</div></Live>
  </div>
 </div>;
 else body=<div style={{...diagramStyle,display:'flex',flexDirection:'column',justifyContent:'center'}}>{label('怎么判断真的改善了？')}
  <div style={{marginTop:32,display:'flex',gap:15}}>
  {[['选','一类常见改动'],['记','各环节花的时间'],['改','先只动一个环节'],['复查','时间短了，证据不减']].map(([k,v],i)=><Live frame={frame} at={at(i,20+i*25)} key={k} style={{...pane,padding:21,flex:1,borderTop:`4px solid ${i===3?accent:forest}`}}><div style={{fontSize:35,fontWeight:760,marginBottom:14}}>{k}</div><div style={info}>{v}</div></Live>)}
  </div>
 </div>;
 return <AbsoluteFill style={{fontFamily:main,background:paper,color:ink,overflow:'hidden'}}>
  <AbsoluteFill style={{backgroundImage:'radial-gradient(#334b3520 1px,transparent 1px)',backgroundSize:'19px 19px',opacity:.19}}/>
  <div style={{position:'absolute',left:57,right:57,top:30,display:'flex',alignItems:'center',gap:10,fontSize:17,fontWeight:680}}><span style={{height:10,width:10,borderRadius:2,background:forest}}/>测试游记<span style={{color:muted}}> / 工程实践</span><span style={{marginLeft:'auto',color:muted,fontFamily:mono}}>ARTICLE FILM / {String(index+1).padStart(2,'0')}</span></div>
  <div style={{position:'absolute',left:57,right:57,top:62,...rule}}/>
  {body}
  {cut?<div style={{position:'absolute',left:48,right:48,bottom:49,display:'flex',justifyContent:'center',textAlign:'center'}}><span style={{borderRadius:6,background:'#202923',color:'#fffdf3',fontWeight:550,fontSize:24,maxWidth:950,padding:'7px 16px',lineHeight:1.35}}>{cut.text}</span></div>:null}
  <div style={{position:'absolute',left:57,right:57,bottom:18,display:'grid',gridTemplateColumns:'repeat(7,1fr)',gap:8}}>
  {chapters.map((s,i)=><div key={s} style={{fontSize:12,color:i===index?ink:muted}}><div style={{height:2,marginBottom:7,background:i<=index?forest:line}}/>{s}</div>)}
  </div>
  {slide.cues.map(({from,to,file})=><Sequence key={file} from={from} durationInFrames={to-from} layout="none"><Audio src={staticFile(file)}/></Sequence>)}
 </AbsoluteFill>;
};
