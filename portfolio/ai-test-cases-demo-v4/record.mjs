import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdtempSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
const [out, project]=process.argv.slice(2);
const req=createRequire(join(project,'package.json'));
let pw;try {pw=req('playwright-core')} catch {pw=req(process.env.PLAYWRIGHT_CORE_PATH)}
const {chromium}=pw,{Client}=req('@modelcontextprotocol/sdk/client/index.js'),{StdioClientTransport}=req('@modelcontextprotocol/sdk/client/stdio.js');
const home=mkdtempSync(join(tmpdir(),'portfolio-codex-')),server=join(project,'dist/codex-test-cases/plugin/codex-test-cases/server/server.cjs');
const client=new Client({name:'portfolio-offline-replay',version:'1.0'});
await client.connect(new StdioClientTransport({command:process.execPath,args:[server],env:{PATH:process.env.PATH,CODEX_TEST_CASE_DB:join(home,'demo.sqlite')}}));
const resource=(await client.readResource({uri:'ui://test-case-workbench/board.html'})).contents[0].text;
const shell=readFileSync(join(out,'host.html'),'utf8'),fixture=readFileSync(join(out,'fixture.html'),'utf8');
const http=createServer((q,r)=>{r.setHeader('Content-Type','text/html; charset=utf-8');r.statusCode=['/','/board','/fixture'].includes(q.url)?200:404;r.end(q.url==='/board'?resource:q.url==='/fixture'?fixture:q.url==='/'?shell:'');});
await new Promise(r=>http.listen(0,'127.0.0.1',r));
let browser;const base='http://127.0.0.1:'+http.address().port,events=[],messages=[];
const allowed=new Set(['workbench_panel','create_suite','open_suite','update_suite','start_run','record_run_results','get_run']);
async function call(name,args){assert(allowed.has(name));const r=await client.callTool({name,arguments:args});assert(!r.isError,JSON.stringify(r.content));events.push(name);return r;}
let suite;
const row=(topic,priority,steps,expected)=>({topic,category:'收藏清单',precondition:'打开本机虚构清单，禁用外网。',priority,steps:'1. '+steps,expected:'1. '+expected});
const added=row('重复收藏不增加副本','P1','连续点击两次「收藏」。','清单始终只有一条「湖边散步」。');
try{
 browser=await chromium.launch({executablePath:process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--disable-background-networking','--hide-scrollbars']});
 const ctx=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
 await ctx.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
 const p=await ctx.newPage(),errs=[];p.on('pageerror',e=>errs.push(e.message));p.setDefaultTimeout(10000);
 await p.exposeFunction('mcpTool',async o=>call(o.name,o.arguments));
 await p.exposeFunction('recordMessage',params=>messages.push(params));
 await p.goto(base);
 await p.evaluate(()=>{
  const frame=document.querySelector('#board');
  window.deliver=result=>frame.contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},'*');
  window.addEventListener('message',async ({source,data:m})=>{
   if(source!==frame.contentWindow || !m?.method)return;
   const send=obj=>source.postMessage({jsonrpc:'2.0',...obj},'*');
   if(m.method==='ui/initialize')send({id:m.id,result:{protocolVersion:m.params.protocolVersion,hostInfo:{name:'MCP Apps 本机演示宿主',version:'1'},hostCapabilities:{serverTools:{},message:{text:{}}},hostContext:{displayMode:'inline',availableDisplayModes:['inline']}}});
   else if(m.method==='ui/notifications/initialized'){window.deliver(await window.mcpTool({name:'workbench_panel',arguments:{}}));window.boardReady=true;}
   else if(m.method==='tools/call')send({id:m.id,result:await window.mcpTool(m.params)});
   else if(m.method==='ui/message'){await window.recordMessage(m.params);send({id:m.id,result:{isError:false}});}
  });
  frame.src='/board';
 });
 await p.waitForFunction(()=>window.boardReady===true);
 const board=p.frameLocator('#board');
 const shot=async (index,chapter,question,tool,result,detail,focus=false)=>{
  await p.evaluate(o=>globalThis.present(o),{chapter,question,tool,result,detail,focus});
  await p.waitForTimeout(280);
  await p.screenshot({path:join(out,'raw','frame-'+index+'.png'),animations:'disabled'});
 };
 const update=async change=>{const r=await call('update_suite',{suiteId:suite.id,revision:suite.revision,changes:[change]});suite=r.structuredContent.suite;await p.evaluate(r=>deliver(r),r);};
 const title='收藏清单 · 功能验收';
 const cr=await call('create_suite',{title,requirement:'收藏一条路线以后可在清单查看；连续收藏同一路线不能出现副本。',context:'只在本机虚构测试页运行，禁止访问外网或真实数据。',cases:[
  row('第一次收藏显示路线','P1','点击「收藏」。','清单显示一条「湖边散步」。'),
  row('收藏按钮文案（旧用例）','P3','查看页面上的按钮。','显示「收藏」。'),
  row('刷新后保留收藏','P1','收藏后刷新页面。','仍显示已收藏的路线。')
 ]});
 suite=cr.structuredContent.suite;
 await p.evaluate(r=>deliver(r),cr);
 await board.getByRole('heading',{name:title}).waitFor();
 await board.getByRole('button',{name:'适应画布'}).click();
 await shot(1,'01 · 生成并保存','按需求生成收藏清单用例，保存并打开脑图。','create_suite','已保存 3 条 · 版本 1','用例由脚本提供给真实插件，画面是插件自己的脑图。');
 const original=suite.id;
 await update({action:'add',entry:added});
 const id=suite.cases.find(x=>x.topic===added.topic).id;
 const addedCheck=board.getByRole('checkbox',{name:'选择 '+added.topic,exact:true});
 await addedCheck.waitFor();
 assert(suite.cases.length===4 && suite.revision===2);
 await shot(2,'02 · 新增一条','再补一条「重复收藏不增加副本」。','update_suite','新增 1 条 · 版本 2','同一个工作区，脑图同步新增。');
 await update({action:'update',caseId:id,entry:{priority:'P0',expected:'1. 清单只有一条「湖边散步」，总数为 1。'}});
 assert(suite.cases.find(x=>x.id===id).priority==='P0' && suite.revision===3);
 await shot(3,'03 · 修改已有用例','把重复收藏改为 P0，预期写清楚：只有一条，总数是 1。','update_suite','P1 → P0 · 版本 3','原用例 ID 不变，其他用例保持原样。');
 const del=suite.cases.find(x=>x.topic.includes('旧用例')).id;
 await update({action:'remove',caseId:del});
 await board.getByRole('checkbox',{name:'选择 收藏按钮文案（旧用例）',exact:true}).waitFor({state:'detached'});
 assert(suite.id===original && suite.cases.length===3 && suite.revision===4 && !suite.cases.some(x=>x.id===del));
 await shot(4,'04 · 删除旧用例','删掉「收藏按钮文案」那条，其余都保留。','update_suite','删除后 3 条 · 版本 4','只改这个演示工作区，不动其他数据。');
 await addedCheck.check();
 await board.getByRole('textbox',{name:/执行目标/}).fill('本机虚构收藏清单');
 await board.getByRole('button',{name:'交给 Codex 执行（1）'}).click();
 await board.getByText(/已交给 Codex/).waitFor();
 assert.equal(messages.length,1);
 const handoff=JSON.stringify(messages[0]);
 assert(handoff.includes(id)&&handoff.includes('版本：4')&&handoff.includes('本机虚构收藏清单'));
 assert(!handoff.includes(del)&&suite.cases.filter(x=>x.id!==id).every(x=>!handoff.includes(x.id)));
 await shot(5,'05 · 勾选执行范围','只执行这条 P0，目标是本机虚构收藏清单。','脑图按钮 · 交给 Codex 执行','已选 1 条 · 版本 4','只冻结所选用例，另外两条不执行。');
 const run=(await call('start_run',{suiteId:suite.id,revision:suite.revision,caseIds:[id],target:'本机虚构收藏清单'})).structuredContent.run;
 assert(run.cases.length===1&&run.cases[0].id===id&&run.revision===4);
 const f=await ctx.newPage(); await f.goto(base+'/fixture');
 await f.screenshot({path:join(out,'raw','frame-6-before.png')});
 await f.getByRole('button',{name:'收藏',exact:true}).click(); await f.waitForTimeout(450);
 await f.screenshot({path:join(out,'raw','frame-6-first.png')});
 await f.getByRole('button',{name:'收藏',exact:true}).click();
 const total=await f.locator('#entries li').count(),text=await f.locator('#entries').innerText();
 assert.equal(total,1);assert.equal(text,'湖边散步');
 await f.screenshot({path:join(out,'raw','frame-6.png')});
 const evidence='本机浏览器实测：连续点击「收藏」两次；界面中「湖边散步」只出现 1 次，清单总数为 1。';
 await call('record_run_results',{suiteId:suite.id,runId:run.id,outcomes:[{caseId:id,status:'passed',evidence}]});
 const replay=(await call('get_run',{suiteId:suite.id,runId:run.id})).structuredContent.run;
 assert.equal(replay.outcomes[0].status,'passed');assert.equal(replay.outcomes[0].evidence,evidence);
 const reopen=await call('open_suite',{suiteId:suite.id});await p.evaluate(r=>deliver(r),reopen);
 await board.getByText(/最近执行 · 版本 4 · 已记录 1\/1/).click();
 const shown=board.getByText(evidence,{exact:true});await shown.waitFor();await shown.scrollIntoViewIfNeeded();
 await shot(7,'07 · 回写结论和证据','查看本次执行记录，展示结论与实际观察。','record_run_results','通过 · 保留版本 4','点两次，实际只保留一条路线。',true);
 assert.deepEqual(errs,[]);
 writeFileSync(join(out,'raw','evidence.json'),JSON.stringify({recording:'实际插件 MCP Apps 脑图和本地数据库；左侧为脚本复现，不是 Codex 客户端或真实模型聊天。',fixture:'本机虚构单页，禁止外网',events,states:[{revision:1,total:3},{revision:2,total:4},{revision:3,priority:'P0'},{revision:4,total:3}],run:{revision:4,selected:1,status:'passed',evidence},verifiedHandoff:true,browser:{clicks:2,total,text}},null,2));
}finally{await browser?.close();await client.close();http.close();}
