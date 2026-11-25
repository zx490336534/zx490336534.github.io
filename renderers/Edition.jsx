import React from 'react';
import {AbsoluteFill,Sequence,Audio,staticFile,interpolate,Easing,useCurrentFrame} from 'remotion';
const themes={cache:['#f1efe8','#242c30','#a33b33','#345f69','#e4ddd2'],eli:['#f0ede4','#312943','#b15f30','#5b4d83','#e4dced'],test:['#ebeee6','#202f2a','#a44a31','#2d6453','#d7e3d9']};
const font='"PingFang SC","Hiragino Sans GB",sans-serif',mono='Menlo, monospace';
const rise=(f,start,d=13)=>interpolate(f,[start,start+d],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.bezier(.16,.8,.23,1)});
const clamp=(x,l,r)=>Math.max(l,Math.min(r,x));
function Visual({data,slide,index,f}){
 const [paper,ink,a,b,wash]=themes[data.palette]||themes.eli;
 const rows=slide.items,n=rows.length, nCue=slide.cues.length;
 const cue=(i)=>slide.cues[clamp(i,0,nCue-1)]?.from??2;
 const moment=(i)=> i===0?5:cue(i);
 const shown=(i)=>rise(f,moment(i));
 const live=Math.max(0,...rows.map((_,i)=>f>=moment(i)?i:0));
 const block={border:'1px solid '+b+'54',background:'#ffffffb6',borderRadius:15};
 if(slide.mode==='rail'||slide.mode==='routes'){
   const x=[210,590,970], travel=rise(f,8,28), step=slide.mode==='routes'?live:Math.max(0,live-1);
   const pos=step<=0?95+travel*115:x[step-1]+(x[step]-x[step-1])*rise(f,moment(step),23);
   const burst=data.palette==='cache'&&slide.mode==='routes' ? (index===1?3:7) : 1;
   return <div style={{position:'absolute',left:52,right:52,top:146,height:408}}>
      <svg viewBox="0 0 1176 350" style={{position:'absolute',width:'100%',height:350}}>
      <path d="M103 213H1073" stroke={wash} strokeWidth="10" strokeLinecap="round"/><path d={`M103 213H${Math.max(103,pos)}`} stroke={b} strokeWidth="5" strokeLinecap="round"/>
      {x.map((q,i)=><g key={q}><path d={`M${q} 171V213`} stroke={b} opacity={shown(i)*.75} strokeWidth="2"/><circle cx={q} cy="213" r={i===step?14:9} fill={i===step?a:b} opacity={shown(i)}/></g>)}
      {Array.from({length:burst},(_,i)=>{const z=burst===1?pos:(pos-i*24); return <rect key={i} x={z-13} y={201+(i%2)*7} width={burst===1?26:20} height={burst===1?24:18} rx="5" fill={burst>1?a:b} opacity={rise(f,8+i*5)*(.98-i*.06)}/>})}
      {slide.mode==='routes'?<path d="M591 253h163q65 0 65-43" fill="none" stroke={a} strokeWidth="3" strokeDasharray="6 10" opacity={rise(f,moment(1),15)}/>:null}
      </svg>
      {rows.map(([k,v],i)=><div key={k} style={{position:'absolute',width:320,left:x[i]-160,top:(1-shown(i))*17+50,opacity:shown(i),...block,padding:'16px 20px',minHeight:102,borderTop:`4px solid ${i===live?a:b}`}}><div style={{fontSize:31,fontWeight:750,marginBottom:7}}>{k}</div><div style={{fontSize:20,opacity:.76}}>{v}</div></div>)}
      <div style={{position:'absolute',bottom:52,left:36,fontFamily:mono,fontSize:14,color:b,letterSpacing:2}}> {data.palette==='cache'?'CACHE / REQUEST PATH':'EVIDENCE / STATE PATH'} </div>
    </div>
 }
 if(slide.mode==='grid'||slide.mode==='tree')return <div style={{position:'absolute',left:68,right:68,top:142,height:435}}>
  <svg viewBox="0 0 1144 410" style={{position:'absolute',width:'100%',height:410}}>
  {rows.slice(1).map((r,i)=>{const y=68+108*i;const d=slide.mode==='tree'?`M355 174H544V${y}H728`:`M390 ${y}H600V176H752`;return <path key={y} d={d} fill="none" stroke={i===live-1?a:b} strokeWidth={i===live-1?5:3} pathLength="1" strokeDasharray="1" strokeDashoffset={1-shown(i+1)} opacity=".85"/>})}
  </svg>
  {(slide.mode==='tree'?[rows[0]]:[rows[3]]).map(([k,v])=><div key={k} style={{...block,position:'absolute',top:126,left:slide.mode==='tree'?46:753,width:345,padding:20,background:wash,fontSize:30,fontWeight:750}}>{k}<div style={{fontSize:20,fontWeight:500,marginTop:8}}>{v}</div></div>)}
  {(slide.mode==='tree'?rows.slice(1):rows.slice(0,3)).map(([k,v],i)=><div key={k} style={{...block,position:'absolute',left:slide.mode==='tree'?728:52,top:23+i*108,width:334,padding:'13px 19px',opacity:shown(Math.min(i+1,n-1)),transform:`translateX(${(1-shown(i+1))*-24}px)`}}><b style={{fontSize:27}}>{k}</b><div style={{fontSize:17,marginTop:4,opacity:.76}}>{v}</div></div>)}
 </div>;
 if(slide.mode==='stamps'){
 const counts=[1,1,2,3];
 return <div style={{position:'absolute',left:92,right:92,top:180}}>
  <div style={{display:'grid',gridTemplateColumns:'repeat(4, 1fr)',gap:17,alignItems:'center'}}>
  {rows.map(([k,v],i)=><div key={k} style={{...block,opacity:shown(i),padding:'21px 19px',height:185,transform:`translateY(${(1-shown(i))*12}px)`}}><span style={{display:'inline-block',color:i===1?a:b,transform:`rotate(${(1-shown(i))*-18-6}deg)`,fontSize:17,fontFamily:mono,border:`2px solid ${i===1?a:b}`,padding:'5px 8px',marginBottom:13}}>{i===1?'重复':'计入'}</span><div style={{fontSize:30,fontWeight:750}}>{k}</div><div style={{fontSize:18,marginTop:12}}>{v}</div></div>)}
  </div><div style={{fontSize:37,fontWeight:800,color:b,marginTop:31,letterSpacing:-1}}>不同日期：<span style={{color:a,fontFamily:mono}}>{counts[live]} / 3</span></div>
 </div>
 }
 if(slide.mode==='phones')return <div style={{position:'absolute',left:100,right:100,top:160,display:'flex',gap:30,alignItems:'end',height:355}}>
  {rows.map(([k,v],i)=><div key={k} style={{flex:i===0?1.45:i===1?1.14:.7,opacity:shown(i),transform:`translateY(${(1-shown(i))*15}px)`}}>
   <div style={{...block,height:[230,166,260][i],padding:18,display:'grid',gridTemplateRows:'30px 1fr 17px',gap:9,border:`3px solid ${b}`}}><div style={{borderRadius:4,background:b+'30'}}/><div style={{background:wash,borderRadius:7,border:'1px solid '+b+'50'}}/><div style={{maxWidth:85,borderRadius:3,background:a+'65'}}/></div>
   <div style={{fontSize:25,fontWeight:780,marginTop:12}}>{k}</div><div style={{fontSize:19,opacity:.7,marginTop:4}}>{v}</div>
  </div>)}
 </div>;
 if(slide.mode==='compare')return <div style={{position:'absolute',left:76,right:76,top:196,display:'grid',gridTemplateColumns:'1fr 1fr',gap:29}}>
  {rows.map(([k,v],i)=><div key={k} style={{...block,background:i===0?'#ffffff91':wash,borderLeft:`6px solid ${i===0?a:b}`,padding:31,height:244,opacity:shown(i),transform:`translateY(${(1-shown(i))*20}px)`}}>
    <div style={{fontFamily:mono,fontSize:14,letterSpacing:3,color:i===0?a:b}}>CASE 0{i+1}</div><div style={{fontSize:39,fontWeight:810,margin:'24px 0 17px'}}>{k}</div><div style={{fontSize:24,opacity:.75}}>{v}</div>
  </div>)}
 </div>;
 return <div style={{position:'absolute',left:143,right:143,top:169,display:'grid',gap:13}}>
 {rows.map(([k,v],i)=><div key={k} style={{...block,display:'flex',alignItems:'center',gap:27,padding:'15px 25px',minHeight:65,opacity:shown(i),transform:`translateX(${(1-shown(i))*-15}px)`,background:live===i?wash:'#ffffffba'}}><div style={{fontFamily:mono,fontSize:19,color:a}}>0{i+1}</div><div style={{fontSize:26,fontWeight:790,minWidth:225}}>{k}</div><div style={{fontSize:22,opacity:.76}}>{v}</div>{slide.mode==='metrics'?<div style={{marginLeft:'auto',width:20,height:20,borderRadius:99,border:'3px solid '+b}}/>:null}</div>)}
 </div>;
}
export const Scene=({data,slide,index})=>{
 const f=useCurrentFrame(), [paper,ink,a,b,wash]=themes[data.palette]||themes.eli;
 const cue=slide.cues.find(c=>f>=c.from&&f<c.to);
 return <AbsoluteFill style={{background:paper,color:ink,fontFamily:font,overflow:'hidden'}}>
 <AbsoluteFill style={{backgroundImage:`radial-gradient(${ink}26 1px,transparent 1px)`,backgroundSize:'21px 21px',opacity:.21}}/>
 <div style={{position:'absolute',left:52,right:52,top:28,display:'flex',alignItems:'center',gap:13,height:30,borderBottom:'1px solid '+ink+'38',paddingBottom:10,fontSize:17,fontWeight:650}}><div style={{width:8,height:8,borderRadius:1,background:a}}/>测试游记 <span style={{opacity:.58}}>/ {data.topic}</span><span style={{marginLeft:'auto',color:b,fontFamily:mono,fontSize:14}}>ARTICLE FILM / {String(index+1).padStart(2,'0')}</span></div>
 <div style={{position:'absolute',left:60,right:60,top:91,fontWeight:800,fontSize:slide.heading.length>16?48:56,letterSpacing:-1,opacity:rise(f,0),transform:`translateY(${(1-rise(f,0))*13}px)`}}>{slide.heading}</div>
 <Visual data={data} slide={slide} index={index} f={f}/>
 <div style={{position:'absolute',left:60,right:60,top:535,fontSize:18,color:b,opacity:rise(f,18)}}>{slide.foot}</div>
 {cue?<div style={{position:'absolute',left:43,right:43,bottom:49,textAlign:'center',display:'flex',justifyContent:'center'}}><div style={{background:ink,color:'#fffdf4',padding:'7px 17px',borderRadius:7,fontSize:24,fontWeight:540,lineHeight:1.33,maxWidth:1050}}>{cue.text}</div></div>:null}
 <div style={{position:'absolute',left:54,right:54,bottom:22,display:'grid',gap:8,gridTemplateColumns:`repeat(${data.slides.length},1fr)`}}>{data.slides.map((s,i)=><div key={i} style={{background:i<=index?b:wash,height:3}}/>)}</div>
 {slide.cues.map(c=><Sequence key={c.file} from={c.from} durationInFrames={c.to-c.from} layout="none"><Audio src={staticFile(c.file)}/></Sequence>)}
 </AbsoluteFill>;
}
