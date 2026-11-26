# AI 测试用例脑图 · Codex 插件章节
成片保留上一版 Web 工作区实际录制（Skill、MCP、对话编辑、CSV/XMind 导出），在 3:20 加入此处的独立插件章节。它不是 Codex 客户端截屏：左边把会话指令固定复现，右边为实际 MCP Apps 用例脑图。插件存储、用例版本、点击后发送范围、执行批次及证据写入全部真实发生在本地隔离环境。执行目标仅是随档提供的虚构收藏清单 HTML，不连接外部系统。
- 插件源码：next-ai-test-cases 提交 6f4143240b92a15b84f39088d402f7bb15ca83af；插件版本 0.1.2。
- 在项目配置好依赖后执行其 build:codex，然后用 node 运行 record.mjs，参数为本目录和项目目录。需要 Playwright Core（可用 PLAYWRIGHT_CORE_PATH 提供）及 Chrome（可用 CHROME_PATH 提供）。请先创建 raw 子目录。脚本使用全新的本地 SQLite 存放用例，并拒绝浏览器的外网请求。
- record.mjs、host.html、fixture.html 是录制输入；raw/frame-*.png 是实际捕获的画面；raw/evidence.json 为清理过的事实清单，不包括主机名、数据库文件和用例 ID。
- voice.tsv / raw/voice-*.mp3 是实际使用的微软 Edge 晓晓语音与台词。assemble.py 的参数是前版成片存放目录，输出本版 MP4、WebP 封面、中文字幕及 chapters.json。前版媒体位于博客主分支 videos/portfolio，对应工程在本分支的同级 ai-test-cases-demo-v3。
