# AI 测试用例脑图：Skill、MCP 和三轮对话编辑

在隔离浏览器中录制公开源码 `next-ai-test-cases@f4de4e1e45c3766e10880c0aacbcae6271cede69` 的完整版。没有真实需求或模型密钥。演示用虚构文档、走真实的只读 MCP stdio、上传实际 Markdown Skill，使用本地固定模型输出，验证真实应用的生成、编辑和交付链路，不评价模型能力。

三轮对话按当前脑图分别执行：
1. 新增同一时段连续提交的用例，保留原始三条。
2. 修改新增用例的优先级和第二步预期，不重生成其它节点。
3. 删除原来的成功预约用例，保留其余三条。

随后用画布手动校对另一个节点，真实下载 CSV 和 XMind，逐字核对两个文件都包含新增、修改，且不含删除项。CSV 还验证了新优先级 P0。

- `SKILL.md`、`fixture.json`、`demo-mcp.mjs` 包含合成示例、只读固定文档和模拟模型输入检查。
- `run.mjs` 实际操作并录制界面，检测每轮对应结果；`evidence.json` 保存通过的跨轮验收。
- `cover.png` / `cover.jpg` 为实际使用的生图原件和录屏片头；没有文字和界面滚动条。阶段标签是解说层。
- `voice.tsv` 和原音轨使用 Microsoft Edge 晓晓普通话 `zh-CN-XiaoxiaoNeural`（+10%）。`assemble.py` 编码并校验 CSV/XMind、音视频和字幕。成片放站点主线 `videos/portfolio/ai-test-cases-demo-v3.mp4`。

重录前将指定公开版本放入 `app/`、安装依赖并将 `demo-mcp.mjs` 复制进 `app/`。建空目录 `home/`。使用 Node 24、Chrome、Python、FFmpeg、cwebp，执行 `node run.mjs` 预演、`node run.mjs --record` 录屏，再执行 `python3 assemble.py`。只使用回环地址及一份虚构文档，不连接外部模型、真实账号或需求系统。临时浏览器资料与数据库不进仓库。
