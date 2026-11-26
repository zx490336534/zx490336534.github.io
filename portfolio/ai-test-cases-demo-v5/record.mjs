import assert from 'node:assert/strict';
import {readFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
const [out,project]=process.argv.slice(2),req=createRequire(join(project,'package.json'));
const {Client}=req('@modelcontextprotocol/sdk/client/index.js'),{StdioClientTransport}=req('@modelcontextprotocol/sdk/client/stdio.js'),{chromium}=req(process.env.PLAYWRIGHT_CORE_PATH||'playwright-core');
const rows=JSON.parse(readFileSync(join(out,'scenes.json'),'utf8'));
const client=new Client({name:'portfolio-saved-snapshots',version:'1.0'});
mkdirSync(join(out,'preview-store'),{recursive:true});
await client.connect(new StdioClientTransport({command:process.execPath,args:[join(project,'dist/codex-test-cases/plugin/codex-test-cases/server/server.cjs')],env:{PATH:process.env.PATH,CODEX_TEST_CASE_DB:join(out,'preview-store','isolated.sqlite')}}));
const template=(await client.readResource({uri:'ui://test-case-workbench/board.html'})).contents[0].text;await client.close();
const host=readFileSync(join(out,'host.html'),'utf8')
 .replace('对话复现 · 非客户端实录','真实对话摘录 · 非桌面截屏')
 .replace('真实插件 · 本机隔离环境','真实插件 · 工作区快照')
 .replace('虚构需求 · 聊天文字为固定复现，脑图、用例版本、执行和结果来自实际本机操作。','虚构演示 · 左边是实际 Codex 回复（指令为短摘要），右边是插件保存的工作区、执行和证据快照。')
 .replaceAll('Codex 回复复现 · ','');
const h=createServer((q,r)=>{r.setHeader('Content-Type','text/html; charset=utf-8');let i=Number(q.url.split('/').at(-1))-1;r.end(rows[i]?template.replace('<div id="root"></div>','<script id="test-case-workbench-data" type="application/json">'+JSON.stringify(rows[i].view).split('<').join('\\u003c')+'</script><div id="root"></div>'):host);});
await new Promise(r=>h.listen(0,'127.0.0.1',r));
const base='http://127.0.0.1:'+h.address().port;
const b=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--hide-scrollbars','--disable-background-networking']});
try{
 const p=await b.newPage({viewport:{width:1440,height:900}});
 await p.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());await p.goto(base);
 for(const {num,...row} of rows){
  await p.evaluate(({row,num})=>{window.present(row);document.querySelector('#board').src='/board/'+num;},{row,num});
  const f=p.frameLocator('#board');
  await f.getByText(new RegExp('版本 '+row.view.suite.revision+' · '+row.view.suite.cases.length+' 条用例')).first().waitFor();
  if(num===5){
   const label=f.getByRole('checkbox',{name:'选择 重复收藏不增加副本',exact:true});
   await label.check();assert(await label.isChecked());
   assert.equal(await f.getByRole('checkbox',{checked:true}).count(),1);
   await f.getByRole('textbox',{name:/执行目标/}).fill('本机虚构收藏清单');
  }
  if(num>=6){
   const detail=f.getByText(/最近执行 · 版本 5/);
   await detail.click();
   await f.getByText(/重复收藏不增加副本/).last().scrollIntoViewIfNeeded();
  }
  await p.waitForTimeout(260);
  await p.screenshot({path:join(out,'raw','frame-'+num+'.png')});
 }
}finally{await b.close();h.close();}
