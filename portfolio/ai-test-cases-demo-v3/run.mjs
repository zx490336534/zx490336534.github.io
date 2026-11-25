import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import {mkdtemp,readFile,readdir,writeFile,mkdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const cwd=process.cwd(), record=process.argv.includes('--record');
const fixture=JSON.parse(await readFile(join(cwd,'fixture.json'),'utf8'));
const appDir=join(cwd,'app'); const skillFile=join(cwd,'SKILL.md'); const modelLog=join(cwd,'mcp-used.log'); await rm(modelLog,{force:true}); const app=await readFile(join(cwd,'cover.jpg'));
const output=join(cwd,record?'raw':'trial');
await rm(output,{recursive:true,force:true}); await mkdir(output,{recursive:true}); await mkdir(join(output,'downloads'));
const records=[];
let requests=0;
const server=createServer(async(req,res)=>{
 try{
  if(req.url==='/' && req.method==='GET'){
   res.writeHead(200,{'content-type':'image/jpeg'});return res.end(app);
  }
  if(req.url==='/v1/chat/completions'&&req.method==='POST'){
   const data=JSON.parse(Buffer.concat(await Array.fromAsync(req)).toString('utf8'));
   if(data.model!=='fixture-model'||req.headers.authorization!=='Bearer loopback-not-a-secret') throw new Error('unexpected model connection');
   const system=data.messages.find(x=>x.role==='system')?.content||'';
   const input=JSON.parse(data.messages.at(-1).content);
   if(system.includes('只响应最新用户消息')){
    if(!input.skills?.some(x=>x.name===fixture.skillName)) throw new Error('chat did not retain enabled skill');
    const turn=fixture.turns.findIndex(x=>x.prompt===input.messages?.at(-1)?.content);
    if(turn<0) throw new Error('unexpected chat instruction');
    function find(n,title){if(n.data?.text===title)return n;for(const c of (n.children||[])){const exact=find(c,title);if(exact)return exact;}}
    let operations;
    if(turn===0){
      if(find(input.tree,fixture.added)||!find(input.tree,fixture.deleted))throw new Error('unexpected initial chat tree');
      operations=[{op:'addCase',category:'基础预约',precondition:'目标时段无人预约',case:{topic:fixture.added,priority:'P1',steps:'1. 提交该时段预约\n2. 再次提交同一时段',expected:'1. 创建一条预约\n2. 不再创建预约'}}];
    } else if(turn===1){
      const current=find(input.tree,fixture.added); if(!current?.data.uid)throw new Error('previous add not present');
      const id=current.data.uid;
      operations=[{op:'priority',id,priority:'P0'},{op:'updateCase',id,steps:'1. 提交该时段预约\n2. 再次提交同一时段',expected:'1. 创建一条预约\n2. 系统仍只有 1 条有效预约'}];
    } else {
      const current=find(input.tree,fixture.deleted); const revised=find(input.tree,fixture.added);
      if(!current?.data.uid||revised?.data.priority!=='P0'||!JSON.stringify(revised).includes('系统仍只有 1 条有效预约'))throw new Error('earlier turns did not persist');
      operations=[{op:'remove',id:current.data.uid}];
    }
    await sleep(record?1100:170);
    requests++;records.push({kind:'fixture-chat-response',turn:turn+1});
    res.writeHead(200,{'content-type':'application/json'});
    return res.end(JSON.stringify({id:'fixture-'+requests,choices:[{index:0,message:{role:'assistant',content:JSON.stringify({assistantReply:fixture.turns[turn].reply,operations})},finish_reason:'stop'}]}));
   }
   if(input.requirement!==fixture.prompt || input.documents?.length!==1 || input.documents[0]?.text!==fixture.document || !input.skills?.some(x=>x.name===fixture.skillName&&x.instructions.includes('原预约仍然有效'))) throw new Error('model request did not include exact MCP document and enabled Skill');
   const all=fixture.modules.flatMap(x=>x.cases);
   const title=input.targetModule?.title;
   let payload;
   if(system.includes('每个模块含 id、title'))payload={summary:'已生成 3 条用例，覆盖正常预约、满员和取消释放。',modules:fixture.modules.map(({cases,...x})=>x)};
   else if(title)payload={summary:title,cases:all.filter(x=>x.category===title)};
   else if(system.includes('从 1. 开始编号'))payload={summary:'已生成 3 条用例，覆盖正常预约、满员和取消释放。',cases:all};
   else throw new Error('unrecognized generation request');
   requests++; records.push({kind:'fixture-response',module:title??null,index:requests});
   await new Promise(r=>setTimeout(r,record?(title?1250:1450):240));
   res.writeHead(200,{'content-type':'application/json'});
   return res.end(JSON.stringify({id:'fixture-'+requests,object:'chat.completion',choices:[{index:0,message:{role:'assistant',content:JSON.stringify(payload)},finish_reason:'stop'}]}));
  }
  res.writeHead(404);res.end();
 }catch(err){console.error(err.message);res.writeHead(422,{'content-type':'application/json'});res.end('{"error":{"message":"fixture response mismatch"}}');}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r)); const gateway='http://127.0.0.1:'+server.address().port;
const portLease=createServer();
await new Promise(r=>portLease.listen(0,'127.0.0.1',r));
const portNumber=portLease.address().port;
await new Promise(r=>portLease.close(r));
const url='http://127.0.0.1:'+portNumber;
await writeFile(join(appDir,'mcp.json'),JSON.stringify({mcpServers:{demo:{type:'stdio',command:process.execPath,args:[join(appDir,'demo-mcp.mjs'),join(cwd,'fixture.json'),modelLog],allowedOrigins:['https://docs.example.test'],name:'示例需求库 · 只读',documentTool:'read_document',urlArgument:'url'}}}));
const next=spawn(process.execPath,[join(appDir,'node_modules/next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port',String(portNumber)],{
 cwd:appDir,stdio:['ignore','pipe','pipe'],env:{PATH:process.env.PATH,HOME:join(cwd,'home'),TMPDIR:tmpdir(),NODE_ENV:'development',NEXT_TELEMETRY_DISABLED:'1',TEST_CASES_LOOPBACK:'1',TEST_CASES_DB_PATH:join(output,'demo.sqlite'),OPENAI_BASE_URL:gateway+'/v1',OPENAI_MODEL:'fixture-model',OPENAI_API_KEY:'loopback-not-a-secret'}
});
next.stdout.on('data',b=>process.stdout.write(b));
next.stderr.on('data',b=>process.stderr.write(b));
const dir=await mkdtemp(join(tmpdir(),'portfolio-tool-demo-'));
const bin='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const chrome=spawn(bin,['--headless=new','--disable-background-networking','--no-first-run','--disable-sync','--mute-audio','--remote-debugging-port=0','--user-data-dir='+dir,'about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let ws;let captures=[];let frames=[]; let started=0;let lastCursor=[680,440];
const labels=[
 ['01','从虚构需求生成','每时段限 1 人 · 满员拒绝 · 取消即释放'],
 ['02','人工校对与编辑','把满员用例的标题写得更明确'],
 ['03','导出并核对','从当前脑图导出 CSV 和 XMind'],
];
try{
 let port,tabs;
 for(let i=0;i<90;i++){try{port=+(await readFile(join(dir,'DevToolsActivePort'),'utf8')).split('\n')[0];tabs=await(await fetch('http://127.0.0.1:'+port+'/json')).json();break;}catch{await sleep(85)}}
 ws=new WebSocket(tabs.find(x=>x.type==='page').webSocketDebuggerUrl);
 await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
 const pending=new Map(); let seq=0;
 ws.onmessage=e=>{
  const m=JSON.parse(e.data);
  if(m.method==='Page.screencastFrame'){
   const p=m.params;
   const at=p.metadata.timestamp || Date.now()/1000;
   const name='frame-'+String(frames.length).padStart(5,'0')+'.jpg';
   frames.push({at,name});
   captures.push(writeFile(join(output,name),Buffer.from(p.data,'base64')));
   void call('Page.screencastFrameAck',{sessionId:p.sessionId});
  }else if(pending.has(m.id)){
   const [r,j]=pending.get(m.id);pending.delete(m.id);if(m.error)j(new Error(m.error.message));else r(m.result);
  }
 };
 function call(method,params={}){const id=++seq;return new Promise((r,j)=>{pending.set(id,[r,j]);ws.send(JSON.stringify({id,method,params}));});}
 async function ev(expression){
  const a=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(a.exceptionDetails)throw new Error(a.exceptionDetails.exception?.description||a.exceptionDetails.text);
  return a.result.value;
 }
 async function waitFor(expr,ms=9000){const edge=Date.now()+ms;while(Date.now()<edge){const v=await ev(expr);if(v)return v;await sleep(140)}throw new Error('timed out: '+expr);}
 function ts(name){records.push({kind:name,time:Math.round(Date.now()-started)/1000});console.log(records.at(-1));}
 async function at(sec){const n=record?sec*1000-(Date.now()-started):160;if(n>0)await sleep(n);}
 async function snap(name){const image=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});await writeFile(join(output,name+'.png'),Buffer.from(image.data,'base64'));}
 async function coords(q){return await waitFor(`(()=>{const e=(${q});if(!e||e.disabled)return;const b=e.getBoundingClientRect();if(b.width<=0||b.height<=0)return;return [Math.round(b.x+b.width/2),Math.round(b.y+b.height/2)]})()`);}
 async function tap(q,n=1){
  const [x,y]=await coords(q); const [a,b]=lastCursor;
  for(let i=1;i<=7;i++){const px=Math.round(a+(x-a)*i/7),py=Math.round(b+(y-b)*i/7);await ev(`window.__pointer?.(${px},${py},false)`);await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:px,y:py});if(record)await sleep(24);}
  await ev(`window.__pointer?.(${x},${y},true)`);
  lastCursor=[x,y];
  await call('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:n});
  await call('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:n});
  if(record)await sleep(115);
  await ev(`window.__pointer?.(${x},${y},false)`);
 }
 const btn=v=>`[...document.querySelectorAll('button')].find(b=>b.getClientRects().length&&(b.innerText.trim()===${JSON.stringify(v)}||b.getAttribute('aria-label')===${JSON.stringify(v)}))`;
 const node=v=>`[...document.querySelectorAll('svg text, svg tspan, svg foreignObject div')].find(e=>e.textContent.trim()===${JSON.stringify(v)}&&e.getBoundingClientRect().width>2)`;
 async function insert(s){await call('Input.insertText',{text:s});}
 async function key(k,code=k,modifiers=0){await call('Input.dispatchKeyEvent',{type:'keyDown',key:k,code,modifiers});await call('Input.dispatchKeyEvent',{type:'keyUp',key:k,code,modifiers});}
 async function download(ext){const t=Date.now()+8000;while(Date.now()<t){const entries=await readdir(join(output,'downloads'));const name=entries.find(x=>x.endsWith(ext));if(name)return name;await sleep(160);}throw new Error('download not found '+ext);}
 await call('Page.enable');
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await call('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:join(output,'downloads')});
 for(let i=0;i<100;i++){try{if((await fetch(url,{signal:AbortSignal.timeout(15000)})).ok)break}catch{};if(i===99)throw new Error('isolated app failed to start');await sleep(500)}
 await call('Page.addScriptToEvaluateOnNewDocument',{source:"Object.defineProperty(navigator,'globalPrivacyControl',{get:()=>true})"});
 await call('Page.navigate',{url});
 await waitFor('document.readyState==="complete"&&!!document.querySelector("textarea")');
 await ev(`(()=>{
  const root=document.body;
  const style=document.createElement('style');style.textContent=\`
  html,body,*{scrollbar-width:none!important}::-webkit-scrollbar{display:none!important}nextjs-portal{display:none!important}
  #demoHead,#demoEnd,#demoCursor,#demoProgress,#demoProof{font-family:-apple-system,'PingFang SC','Helvetica Neue',sans-serif;position:fixed;box-sizing:border-box;z-index:2147483600;pointer-events:none}
  #demoProgress{top:95px;left:25px;width:225px;background:#0c3032;color:#fff;padding:12px 16px;border-radius:13px;box-shadow:0 8px 20px #0c30324d;letter-spacing:.2px}
  #demoProgress b{display:block;font-size:15px;line-height:1.15} #demoProgress small{display:block;font-size:10px;color:#b2ded4;margin-top:5px}
  #demoCursor{top:0;left:0;width:26px;height:27px;transform:translate(-80px,-80px);z-index:2147483646;filter:drop-shadow(0 2px 2px #0005)}
  #demoCursor i{position:absolute;inset:-8px;border-radius:50%;border:2px solid #13ae9d;background:#13ae9d22;opacity:0}#demoCursor svg{position:absolute;inset:0}
  #demoHead,#demoEnd{inset:0;display:none;background:linear-gradient(132deg,#102f30 2%,#173c3a 62%,#26574f 100%);color:#fff;align-items:center;padding:0 110px;overflow:hidden} #demoHead{padding:0;background:#102f30 url('${gateway}') center/cover no-repeat} #demoHead::after{display:none!important}
  #demoHead::after,#demoEnd::after{content:'';position:absolute;right:-140px;bottom:-310px;width:870px;height:870px;border:1px solid #82e4ca44;border-radius:50%;box-shadow:0 0 0 80px #82e4ca12,0 0 0 165px #82e4ca0a,0 0 0 255px #82e4ca09}
  #demoHead section,#demoEnd section{position:relative;z-index:1}
  #demoHead small,#demoEnd small{font-size:20px;color:#a3e4d6;letter-spacing:6px;font-weight:650}
  #demoHead h2,#demoEnd h2{font-weight:750;font-size:85px;line-height:1.12;letter-spacing:0;margin:26px 0;color:white}
  #demoHead p,#demoEnd p{font-size:28px;color:#e1f3ef;margin:0} #demoHead em{display:inline-block;margin-top:46px;border:1px solid #a3e4d68f;border-radius:35px;padding:12px 19px;font-size:17px;font-style:normal;color:#bbefe1}
  #demoProof{display:none;bottom:76px;right:90px;width:600px;padding:27px 34px 28px;color:#143331;background:#f9fffd;border:1px solid #bedad2;border-radius:18px;box-shadow:0 15px 55px #1739384d}
  #demoProof small{color:#1c7565;font-size:16px;font-weight:700} #demoProof h3{margin:10px 0;font-size:26px;color:#123935} #demoProof p{font-size:17px;margin:8px 0}
  \`;root.append(style);
  const el=(id,html)=>{const x=document.createElement('div');x.id=id;x.innerHTML=html;root.append(x);return x;};
  const intro=el('demoHead','');
  const outro=el('demoEnd','<section><small>听白 · 项目实录</small><h2>生成 · 对话编辑 · 导出</h2><p>Skill 与 MCP · 新增、修改、删除 · CSV / XMind</p></section>');
  const prog=el('demoProgress','');const proof=el('demoProof','');
  const cursor=el('demoCursor','<i></i><svg width="24" height="27" viewBox="0 0 24 27"><path fill="#fff" stroke="#073635" stroke-width="1.8" d="M2 1 2 22 7.5 17.4 11 24 14 22.2 10.6 15.6 18.7 14.8Z"/></svg>');
  window.__pointer=(x,y,click)=>{cursor.style.transform='translate('+x+'px,'+y+'px)';cursor.firstElementChild.style.opacity=click?'1':'0';};
  window.__stage=(num,word)=>prog.innerHTML='<b>'+num+' / '+word+'</b><small>虚构需求 · 本地模拟模型</small>';
  window.__view=n=>{intro.style.display=n===1?'flex':'none';outro.style.display=n===2?'flex':'none';if(n)proof.style.display='none';prog.style.display=n?'none':'block';cursor.style.display=n?'none':'block';};
  window.__proof=(title,detail)=>{proof.replaceChildren();for(const [tag,value] of [['small','已核对 · 实际下载文件'],['h3',title],['p',detail],['p','CSV 中包含人工修改后的标题；XMind 文件也已下载。']]){const node=document.createElement(tag);node.textContent=value;proof.append(node);}proof.style.display='block';};
  window.__view(1);
 })()`);
 if(record)await call('Page.startScreencast',{format:'jpeg',quality:87,maxWidth:1440,maxHeight:900,everyNthFrame:1});
 started=Date.now(); ts('record-start');
 await at(6.1); await ev(`__view(0);__stage('01','导入测试 Skill');`);
 const ext='[...document.querySelectorAll("button")].find(b=>b.getClientRects().length&&b.innerText.includes("MCP 与 Skill"))';
 await at(10);await tap(ext);
 await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('示例需求库')`,12000);
 await at(15);
 await tap(btn('上传文件'));
 const doc=await call('DOM.getDocument'); const chooser=await call('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'input[aria-label="选择 Skill 文件"]'});
 await call('DOM.setFileInputFiles',{nodeId:chooser.nodeId,files:[skillFile]});
 await waitFor(`!!document.querySelector('input[aria-label="启用 预约测试规范"]:checked')`,10000);
 ts('real-skill-imported');
 await snap('skill');
 await at(27);await ev(`__stage('02','带入需求来源');`);
 const mcp='[...document.querySelectorAll("dialog[open] label")].find(l=>l.innerText.includes("示例需求库")) input';
 const mcpCheck='[...document.querySelectorAll("dialog[open] label")].find(l=>l.innerText.includes("示例需求库"))?.querySelector("input")';
 if(!await ev(`!!(${mcpCheck})?.checked`))throw new Error('fixture MCP selector not enabled');
 await tap(btn('关闭扩展'));
 await at(34);await tap('document.querySelector("textarea[aria-label=需求正文]")'); await insert(fixture.prompt);ts('requirement-link-entered');
 await at(43);await tap(btn('发送'));ts('generate-clicked');
 await waitFor(`!!(${node('满员时拒绝预约')})&&!!(${node('取消后可以重新预约')})&&[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='CSV'&&!b.disabled)`,20000);
 await waitFor(`document.querySelector('article[aria-label="AI 回复"]')?.innerText.includes('载入 Skill')&&document.querySelector('article[aria-label="AI 回复"]')?.innerText.includes('读取外部资料')`,8000);
 const traceBtn=(v)=>`[...document.querySelectorAll('article[aria-label="AI 回复"] button')].find(b=>b.innerText.includes(${JSON.stringify(v)}))`;
 await at(50);await tap(traceBtn('读取外部资料'));
 if(!await ev(`document.querySelector('article[aria-label="AI 回复"]')?.innerText.includes('已读取 1 份')`)) await tap(traceBtn('读取外部资料'));
 await waitFor(`document.querySelector('article[aria-label="AI 回复"]')?.innerText.includes('已读取 1 份')`,3500);
 await at(55);await tap(traceBtn('载入 Skill'));
 if(!await ev(`document.querySelector('article[aria-label="AI 回复"]')?.innerText.includes('已载入 1 个 Skill')`)) await tap(traceBtn('载入 Skill'));
 await waitFor(`document.querySelector('article[aria-label="AI 回复"]')?.innerText.includes('已载入 1 个 Skill')`,3500);
 if(!(await readFile(modelLog,'utf8')).includes('read_document: study-room-v2'))throw new Error('stdio MCP read not observed');
 ts('real-mcp-read-visible-with-skill');
 await tap(btn('适应画布'));await snap('trace');
 const editor='document.querySelector("textarea[aria-label=修改指令]")';
 const box=(term)=>`document.querySelector('[aria-label="AI 对话区"]')?.innerText.includes(${JSON.stringify(term)})`;
 async function chatTurn(num,start){
   await at(start);
   const turn=fixture.turns[num];
   await ev(`__stage('03',${JSON.stringify(['对话编辑 · 新增','对话编辑 · 修改','对话编辑 · 删除'][num])});`);
   await tap(editor);await insert(turn.prompt);
   if(record)await sleep(3600);
   await tap(btn('发送'));
   await waitFor(box(turn.reply),14000);
   const specific=num===0?`!!(${node(fixture.added)})`:num===1?`!!(${node('2. 系统仍只有 1 条有效预约')})`:`!(${node(fixture.deleted)})`;
   await waitFor(specific,6500);
   ts(['chat-added','chat-modified','chat-deleted'][num]);
   await tap(btn('适应画布'));
   await snap(['chat-add','chat-change','chat-delete'][num]);
 }
 await chatTurn(0,69);
 await chatTurn(1,94);
 await chatTurn(2,119);
 await at(145); await ev(`__stage('04','脑图仍可手工校对');`);
 await tap(btn('折叠历史对话'));
 await tap(btn('折叠对话'));
 await tap(btn('适应画布'));
 await sleep(340);
 await tap(node('满员时拒绝预约'));
 await tap(node('满员时拒绝预约'),2);
 const editable='[contenteditable="true"]';
 await waitFor(`[...document.querySelectorAll(${JSON.stringify(editable)})].some(e=>e.getBoundingClientRect().height>3&&e.innerText.includes('满员时拒绝预约'))`);
 await ev(`(()=>{const e=[...document.querySelectorAll('[contenteditable="true"]')].find(e=>e.getBoundingClientRect().height>3&&e.innerText.includes('满员时拒绝预约'));e.focus();const r=document.createRange();r.selectNodeContents(e);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);})()`);
 await snap('editor');
 const active=await ev(`(()=>{const e=document.activeElement;return {tag:e?.tagName,cls:e?.className,editable:e?.getAttribute('contenteditable'),text:e?.innerText?.slice(0,60)}})()`);
 console.log('active-editor',active);
 const updated='满员时拒绝预约，不新增记录';
 await at(152);await insert(updated);
 await at(157);
 const [bx,by]=await ev(`(()=>{const r=document.querySelector('[aria-label="测试用例脑图画布"]').getBoundingClientRect();return [Math.round(r.left+48),Math.round(r.top+75)]})()`);
 await ev(`__pointer(${bx},${by},true)`);
 await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:bx,y:by});
 await call('Input.dispatchMouseEvent',{type:'mousePressed',x:bx,y:by,button:'left',clickCount:1});
 await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:bx,y:by,button:'left',clickCount:1});
 await ev(`__pointer(${bx},${by},false)`);
 await waitFor(`![...document.querySelectorAll('.smm-node-edit-wrap')].some(e=>e.getBoundingClientRect().height>3)`,3500);
 await sleep(560);
 await waitFor(`!!(${node(updated)})`,4200);
 ts('real-node-edited');
 await snap('edited');
 await at(165);await ev(`__stage('05','导出并核对最终结果');`);
 await at(169); await tap(btn('CSV')); const csv=await download('.csv');
 const csvdata=(await readFile(join(output,'downloads',csv),'utf8')).replace(/^\uFEFF/,'');
 if(csvdata.split(updated).length!==2||csvdata.includes(fixture.deleted)||!csvdata.includes(fixture.added)||!csvdata.includes('系统仍只有 1 条有效预约')||!csvdata.includes('取消后可以重新预约')||!csvdata.includes('目标时段恢复可预约')||!csvdata.includes('原预约仍然有效'))throw new Error('actual CSV content mismatch');
 ts('actual-csv-downloaded-and-verified');
 await at(176);await tap(btn('XMind'));const xmind=await download('.xmind');
 const buf=await readFile(join(output,'downloads',xmind));if(buf.subarray(0,2).toString()!=='PK')throw new Error('invalid XMind zip');
 ts('actual-xmind-downloaded');
 await at(180);await ev(`__proof(${JSON.stringify(updated)},'最终 3 条：对话新增和修改已保留，删除项不在导出中。')`);
 await snap('verified-export');
 await at(192); await ev('__view(2)');
 await at(200); ts('record-end');
 if(record)await call('Page.stopScreencast');
 await Promise.all(captures);
 await writeFile(join(output,'frames.json'),JSON.stringify(frames));
 await writeFile(join(output,'evidence.json'),JSON.stringify({fixtureModel:true,appUnmodified:true,mcpRead:true,skillIncluded:true,chatEdits:['add','update','remove'],deletedTitle:fixture.deleted,addedTitle:fixture.added,modelCalls:requests,events:records,csvRows:3,editedTitle:updated,xmindZip:true},null,2));
 if(record&&frames.length<25)throw new Error('insufficient captured frames');
 console.log('QA passed, frames:',frames.length);
}finally{
 ws?.close();chrome.kill('SIGTERM');next.kill('SIGTERM');server.close();await sleep(400);await rm(dir,{recursive:true,force:true}).catch(()=>{});
}
