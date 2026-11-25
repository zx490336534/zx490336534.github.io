# AI 测试用例脑图：Skill + MCP 完整版实录

长版在隔离浏览器操作开源完整版，使用 `next-ai-test-cases` 的 `f4de4e1e45c3766e10880c0aacbcae6271cede69`。全程仅用虚构的自习室业务。真实界面导入并启用文字 Skill，通过 MCP stdio 只读获取一份固定示例文档；模拟模型的输入验证要求同时包含该文档和启用的 Skill。结果从真实脑图界面手工编辑，下载的 CSV、XMind 均核对了修改结果。演示的是应用链路，不是模型质量测试。

- `SKILL.md`：上传到完整工具的示例测试规范，不含脚本。
- `fixture.json`：模拟需求、独立文档、固定模型响应。
- `demo-mcp.mjs`：只接受唯一虚构链接的本地只读 MCP 服务。
- `run.mjs`：启动隔离的 Next.js 完整版、模拟模型和临时浏览器录制，检查真实执行记录和实际导出文件。
- `cover.png`、`cover.jpg`：实际用在片头和作品页的无字生图封面。阶段标签与鼠标标识是视频解说层；不会改动应用行为。
- `voice.tsv`、12 段音轨：真实 Microsoft Edge 晓晓普通话 `zh-CN-XiaoxiaoNeural`（+10%），一并保存起点与字幕文字。
- `assemble.py`：截图时间轴编码、配音、WebVTT 与 WebP。成片位于站点主分支 `videos/portfolio/ai-test-cases-demo-v2.mp4`。

重录需要 Node 24、Chrome、Python、FFmpeg、cwebp 和 npm/pnpm。请把该版本的公开源码放在本目录的 `app/`，安装依赖，把 `demo-mcp.mjs` 复制到 `app/`，创建空的 `home/`。运行 `node run.mjs` 做快速验收；`node run.mjs --record` 做实际录像；最后 `python3 assemble.py`。没有真实密钥、外部链接请求或用户资料；逐帧素材及临时 SQLite 不进仓库。
