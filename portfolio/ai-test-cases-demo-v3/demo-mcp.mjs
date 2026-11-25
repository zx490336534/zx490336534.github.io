import { readFile, appendFile } from 'node:fs/promises';
import { McpServer } from './node_modules/@modelcontextprotocol/sdk/dist/esm/server/mcp.js';
import { StdioServerTransport } from './node_modules/@modelcontextprotocol/sdk/dist/esm/server/stdio.js';
import { z } from './node_modules/zod/index.js';
const fixture = JSON.parse(await readFile(process.argv[2], 'utf8'));
const log = process.argv[3];
const server = new McpServer({name:'study-room-demo',version:'1.0.0'});
server.registerTool('read_document', { description:'Read the one fictional study-room requirements document.', inputSchema:{ url:z.string() }}, async ({url})=>{
 if(url!==fixture.link)return {isError:true,content:[{type:'text',text:'Only the bundled fictional document is available.'}]};
 await appendFile(log,'read_document: study-room-v2\n');
 return {content:[{type:'text',text:fixture.document}]};
});
await server.connect(new StdioServerTransport());
