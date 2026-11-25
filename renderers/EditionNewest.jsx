import React from 'react';
import {AbsoluteFill,Composition,Sequence,Audio,Img,staticFile,interpolate,Easing,useCurrentFrame,registerRoot} from 'remotion';
const themes={replay:['#f4eee5','#2b3540','#c26c3c','#536981','#d8e2e9'],fragment:['#f2f1e9','#203337','#bc7a32','#447671','#dae7dc'],history:['#f3ebe5','#2e333e','#d04f43','#625d8b','#e3d9ec'],visualtest:['#eaf0ec','#253640','#c0574a','#347868','#cbe9dd'],rag:['#efefe8','#253331','#bf6034','#326753','#d9e7d9'],eval:['#eef0e8','#142e2b','#c75b33','#2e6a57','#cfe6db'],spec:['#eaeff1','#243344','#b85c3b','#476d87','#d4e0e5'],risk:['#f1ebe0','#392f2d','#ac553f','#625b78','#e7dbcb'],cache:['#f1efe8','#242c30','#a33b33','#345f69','#e4ddd2'],eli:['#f0ede4','#312943','#b15f30','#5b4d83','#e4dced'],test:['#ebeee6','#202f2a','#a44a31','#2d6453','#d7e3d9']};
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

 if(slide.mode.endsWith('-map')){
  const s1=rise(f,moment(1),18),s2=rise(f,moment(2),18),red='#d25748';
  const card=(k,v,x,y,on)=> <div key={k} style={{position:'absolute',left:x,top:y,width:270,padding:'11px 15px',borderRadius:9,boxSizing:'border-box',background:on?wash:'#fdfbf8',border:'1px solid '+b+'66',fontSize:19}}><strong>{k}</strong><div style={{fontSize:15,marginTop:4,color:b}}>{v}</div></div>;
  const shell={position:'absolute',top:177,left:72,right:72,height:335};
  if(slide.mode==='replay-map'){
    const missing=index===2;
    return <div style={shell}>
      <svg viewBox="0 0 1136 290" style={{position:'absolute',width:'100%',height:290}}>
        <path d="M243 149H315Q350 149 350 95V58h126M243 149H315q35 0 35 54v38h126" stroke={b} strokeWidth="4" fill="none"/>
        <rect x="230" y="140" width="17" height="17" rx="4" fill={a}/>
        <rect x={350+s1*109} y="51" width="16" height="16" rx="4" fill={b}/>
        <rect x={350+s2*109} y="232" width="16" height="16" rx="4" fill={red}/>
        <path d="M744 57h66v183h-66" stroke={red} strokeWidth="3" fill="none" opacity={s2}/>
      </svg>
      {card(rows[0][0],rows[0][1],32,109,false)}
      {card(rows[1][0],rows[1][1],478,25,false)}
      {card(rows[2][0],rows[2][1],478,207,true)}
      <div style={{position:'absolute',left:850,top:71,width:230,opacity:s2,padding:15,borderRadius:9,background:ink,color:'white',fontFamily:mono,fontSize:22}}>
        <div style={{color:'#fff0c9',fontSize:16}}>{missing?'判断两层':'同一字段位置'}</div>
        <div style={{marginTop:10,fontSize:20}}>{missing?'存在？值？':'$.inStock'}</div>
        <strong>{missing?'缺失 ≠ 空':'true → false'}</strong>
      </div>
    </div>;
  }
  if(slide.mode==='fragment-map'){
    const shine=index===0?1:index===2?s2:s1;
    return <div style={shell}>
     <div style={{position:'absolute',left:8,top:2,width:1060,padding:'13px 21px',background:ink,color:'white',borderRadius:12,fontFamily:mono,fontSize:22}}><span style={{color:'#e9cf9b'}}>报告链接</span>　{index===0?'普通锚点 / 文本片段':index===2?'#:~:text=module%20B-,calculateTotal':'#:~:text=calculateTotal'}</div>
     <div style={{position:'absolute',left:15,top:72,width:733,height:248,border:'2px solid '+b,borderRadius:13,overflow:'hidden',background:'#fffdf6'}}>
       <div style={{height:38,padding:'10px 18px',background:wash,color:b,fontFamily:mono,fontSize:16}}>COVERAGE　/　合成示例</div>
       {[0,1].map((i)=><div key={i} style={{height:49,display:'flex',alignItems:'center',padding:'0 28px',gap:35,background:(index===2?i===1:i===0)?'rgba(255,199,51,'+shine*.32+')':'transparent',fontSize:23,borderTop:'1px solid #92a39650'}}><span style={{width:150}}>module {i?'B':'A'}</span><b style={{fontFamily:mono}}>calculateTotal</b></div>)}
       <div style={{padding:'13px 28px',fontSize:15,color:b}}>保留模块名和函数名，可手动定位。</div>
     </div>
     {rows.map(([k,v],i)=>card(k,v,784,82+i*76,i===live))}
    </div>;
  }
  if(slide.mode==='history-map'){
    const history=index===3;
    const dots=history?['请求匹配','读取历史','不连接真实工具']:['构造订单','错误尝试','转人工'];
    return <div style={shell}>
      <svg viewBox="0 0 1136 304" style={{position:'absolute',width:'100%',height:304}}>
        <path d="M160 192H971" stroke={b} strokeOpacity=".32" strokeWidth="8" strokeLinecap="round"/>
        <path d={'M160 192H'+(515+s2*390)} stroke={b} strokeWidth="3" strokeLinecap="round"/>
        <path d="M543 192v96h250" stroke={red} opacity={history?s2:0} strokeWidth="3" strokeDasharray="7 7" fill="none"/>
        {[162,543,929].map((x,i)=><g key={x}><circle cx={x} cy="192" r={i===1?15:11} fill={i===1?red:b}/><text x={x} y="234" textAnchor="middle" fill={ink} fontSize="20">{dots[i]}</text></g>)}
      </svg>
      {rows.map(([k,v],i)=>card(k,v,[27,409,794][i],20,i===live))}
      <div style={{position:'absolute',right:32,top:262,padding:'8px 16px',background:history?wash:'#fce4db',color:ink,opacity:s2,fontWeight:700,borderRadius:8}}>{history?'历史未命中 → 停止':'最后答复正确，行为仍不通过'}</div>
    </div>;
  }
  return <div style={shell}>
    {[0,1].map((i)=><div key={i} style={{position:'absolute',left:10+i*562,top:4,width:535,height:298,background:'#1e2b36',borderRadius:15,color:'#e9f3ef',overflow:'hidden',boxShadow:'0 5px 18px #2d404440'}}>
      <div style={{height:43,padding:'12px 20px',background:'#2b3d49',fontSize:16}}>{i?'异常遮挡 · 对照':'正常深色页面'}</div>
      <div style={{position:'absolute',top:43,bottom:0,width:98,background:'#242d39',padding:'17px 12px',fontSize:14}}>侧栏</div>
      <svg viewBox="0 0 400 230" style={{position:'absolute',width:410,height:232,left:103,top:53}}>
        <rect x="7" y="8" width="388" height="208" rx="12" fill="#3b5260"/>
        <path d="M40 176H349M40 126H349M40 76H349" stroke="#647e89" strokeWidth="1"/>
        <path d="M58 168L135 123L218 148L302 85L358 118" fill="none" stroke="#96decb" strokeWidth="6" strokeLinejoin="round"/>
        <circle cx="302" cy="85" r="10" fill="#a2dec0"/>
        {i===1?<rect x={370-164*s1} y="80" width={164*s1} height="105" rx="5" fill="#080a0b"/>:null}
        <rect x="7" y="8" width="388" height="208" rx="12" fill="none" opacity={index===1?s1:0.8} stroke="#39b293" strokeWidth="5"/>
        {i===1?<rect x="206" y="80" width="164" height="105" rx="5" fill="none" stroke={red} opacity={s2} strokeWidth="4" strokeDasharray="8 6"/>:null}
      </svg>
    </div>)}
  </div>;
 }

 if(slide.mode==='split'||slide.mode==='windows'||slide.mode==='matrix'||slide.mode==='trace'||slide.mode==='handoff'||slide.mode==='visibility'){
  const Mode=slide.mode;
  const n=rows.length, w=1080/n;
  const late=rise(f,cue(Math.min(nCue-1,n-1)),36);
  const beat=rise(f,cue(1),28);
  if(Mode==='split'||Mode==='windows')return <div style={{position:'absolute',left:96,right:96,top:184,height:325}}>
   <div style={{fontFamily:mono,color:b,fontSize:16,letterSpacing:2,marginBottom:19}}>{data.palette==='rag'?'SOURCE DOCUMENT':'EVIDENCE / WORKING CONTEXT'}</div>
   <div style={{position:'relative',display:'grid',gridTemplateColumns:'1fr '.repeat(n),gap:(Mode==='split'?28*beat:8),background:'#ffffff88',padding:'20px 0',borderTop:'2px solid '+b,borderBottom:'2px solid '+b}}>
   {rows.map(([k,v],i)=><div key={k} style={{padding:'20px 18px',minHeight:110,margin:'0 7px',opacity:.68+shown(i)*.32,background:i===live?wash:'#ffffff',borderBottom:'4px solid '+(i===live?a:b)}}><div style={{fontSize:31,fontWeight:760}}>{k}</div><div style={{fontSize:23,paddingTop:9}}>{v}</div></div>)}
   </div>
   <svg viewBox="0 0 1080 112" style={{width:'100%',height:112,overflow:'visible',position:'absolute',top:201}}>
   {Mode==='split'?<>{[1,2].map((q)=><g key={q} opacity={rise(f,cue(q),24)}><path d={`M${w*q} -185V60`} stroke={a} strokeWidth="3" strokeDasharray="6 7"/><circle cx={w*q} cy="64" r="8" fill={a}/></g>)}</>:<>
   <path d={`M15 30v-13h${w*1.84*beat}v13`} stroke={b} strokeWidth="5" fill="none" opacity={beat}/>
   <path d={`M${w*.96} 69v-13h${w*1.92*late}v13`} stroke={a} strokeWidth="5" fill="none" opacity={late}/>
   <rect x={w*.96} y="-12" width={w*.9} height="30" fill={a} opacity={late*.30}/></>}
   </svg>
  </div>;
  if(Mode==='matrix')return <div style={{position:'absolute',left:90,right:90,top:166,borderRadius:14,overflow:'hidden',border:'1px solid '+b,background:'#ffffffb7'}}>
   <div style={{background:b,color:'white',display:'grid',gridTemplateColumns:'260px 1fr 125px',padding:'12px 24px',fontSize:16,letterSpacing:2}}><span>检查对象</span><span>可核对证据</span><span>审阅</span></div>
   {rows.map(([k,v],i)=><div key={k} style={{display:'grid',gridTemplateColumns:'260px 1fr 125px',padding:'14px 24px',alignItems:'center',borderTop:'1px solid '+b+'32',background:i===live?wash:'white',opacity:.30+shown(i)*.70}}><strong style={{fontSize:27}}>{k}</strong><span style={{fontSize:22}}>{v}</span><span style={{color:i===live?a:b,fontFamily:mono,fontSize:18}}>{i===live?'● 检查中':'○ 证据项'}</span></div>)}
  </div>;
  const rails=Mode==='visibility'?2:n;
  const centers=Array.from({length:rails},(_,i)=>1080*(i+.5)/rails);
  const step=Math.min(live,rails-1);
  const cx=step===0?80+(centers[0]-80)*rise(f,5,19):centers[step-1]+(centers[step]-centers[step-1])*rise(f,moment(step),30);
  return <div style={{position:'absolute',left:100,top:174,width:1080,height:334}}>
   <svg viewBox="0 0 1080 320" style={{position:'absolute',inset:0,width:'100%',height:'100%'}}>
    <defs><linearGradient id="beam"><stop stopColor={a} stopOpacity=".18"/><stop offset="1" stopColor={a} stopOpacity=".68"/></linearGradient></defs>
    <path d="M60 210H1020" stroke={b} strokeOpacity=".22" strokeWidth="11" strokeLinecap="round"/>
    <path d={`M60 210H${cx}`} stroke={b} strokeWidth="5" strokeLinecap="round"/>
    {centers.map((x,i)=><g key={x} opacity={shown(i)}><path d={`M${x} 152V210`} stroke={i===step?a:b} strokeWidth="3" strokeDasharray={Mode==='trace'&&i===2?'7 6':'none'}/><circle cx={x} cy="210" r="8" fill={b}/></g>)}
    {Mode==='visibility'?<path d={`M${cx-18} 180l-100 98h230z`} fill="url(#beam)" opacity={rise(f,9)}/>:null}
    <rect x={cx-16} y="194" width="32" height="32" rx={Mode==='handoff'?5:16} fill={a} opacity={rise(f,6)}/>
    {Mode==='trace'?<path d="M900 210q2 78-172 72H510" stroke={a} strokeWidth="3" fill="none" strokeDasharray="7 7" opacity={late}/>:null}
   </svg>
   {rows.map(([k,v],i)=><div key={k} style={{position:'absolute',left:centers[i]-Math.min(238,480/rails),width:Math.min(476,960/rails),boxSizing:'border-box',top:21+12*(1-shown(i)),padding:'20px 21px 25px',background:i===step?wash:'#ffffffb6',border:'1px solid '+b+'66',borderTop:'4px solid '+(i===step?a:b),opacity:.3+.7*shown(i),borderRadius:11}}><div style={{fontFamily:mono,color:b,fontSize:13,letterSpacing:2,marginBottom:8}}>0{i+1}</div><div style={{fontSize:31,fontWeight:780}}>{k}</div><div style={{fontSize:19,marginTop:7}}>{v}</div></div>)}
  </div>
 }
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
const Scene=({data,slide,index})=>{
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
const OPEN=48;
function Establish({data}){const f=useCurrentFrame();const z=1.014+rise(f,0,48)*.045;return <AbsoluteFill style={{background:'#15251f'}}><Img src={staticFile('establish.webp')} style={{width:'100%',height:'100%',objectFit:'cover',transform:`scale(${z})`,opacity:1-rise(f,40,8)*.42}}/></AbsoluteFill>}
function Film(props){let t=props.cover?OPEN:0;return <AbsoluteFill>{props.cover?<Sequence durationInFrames={OPEN}><Establish data={props}/></Sequence>:null}{props.slides.map((slide,index)=>{const at=t;t+=slide.duration;return <Sequence key={index} from={at} durationInFrames={slide.duration}><Scene data={props} slide={slide} index={index}/></Sequence>})}</AbsoluteFill>}
registerRoot(()=> <Composition id="EditorialArticle" component={Film} defaultProps={{slides:[],palette:'cache',topic:'文章讲解'}} width={1280} height={720} fps={16} durationInFrames={16} calculateMetadata={({props})=>({durationInFrames:props.slides.reduce((n,s)=>n+s.duration,props.cover?OPEN:0)||16})}/>);
