# Codex 对话与插件脑图演示
视频前 3:20 复用已经归档的实际 Web 工作区录制，包含 Skill、MCP、多人轮对话及导出。新章节用本机真实 Codex 回复和插件工作区快照剪辑；左侧的用户指令为短摘要，右侧为插件的实际组件，非原生客户端截图。虚构收藏用例仅在本机演示，未访问业务、真实站点或账号。浏览器批次保留为阻塞；独立的 Node 模拟 DOM 复测针对提供的虚构 HTML，不代表 Chrome 已通过。原始日志、账号与本地数据库不归档。
- 核验后导出的 scenes.json：只保留这篇演示的逐步快照和回复，虚构用例 ID 换成演示占位值。record.mjs 使用 Playwright Core 与同一插件资源录制这些快照（按脚本参数提供本目录和插件源码）。先构建 Test Case Workbench 插件，支持 PLAYWRIGHT_CORE_PATH 指定已装库。
- index.html 和 verify-dom.mjs 为后续复测所用的虚构 fixture，命令仅在 Node VM 内运行单个本地页面的原始事件代码，不发起网络请求。
- raw/frame-*、voice.tsv 和 raw/voice-* 为实际画面、文本和真实微软 Edge 晓晓语音。assemble.py 接收旧 Web 章节所在的成品目录作参数，用于组合此版成片。
