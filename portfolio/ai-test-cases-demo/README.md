# AI 测试用例脑图：作品集实录

这是在隔离浏览器对站点公开工具进行的操作实录。虚构的自习室需求与确定性本地模拟模型都在本目录。演示不衡量真实模型准确率；它复现真实应用如何解析模型接口响应、生成可编辑脑图，并将已提交的人工编辑结果导出。

- 录制页面：站点 master `be67e126f7606695a619c03f288f257f47838d24` 的 `tools/test-cases/index.html`，SHA-256 `509dcc29685715602eaf6f76ac989629a35cf6d59a067a3bacfa9d2f90a827cd`。
- `run.mjs`：本地回环服务器、浏览器交互与录屏。标题、指针、阶段标签及导出核对卡为解说层，不属于工具功能。录屏无账号、无第三方会话、无真实需求或凭据。
- `fixture.json`：演示需求和模型固定输出。代码使用的是只在本地测试有效的占位字符串，不是真实密钥。
- `voice.tsv` 与六段音频：Edge TTS `zh-CN-XiaoxiaoNeural`、速率 +6%，每段的合成原声和起始时间。网页支持独立简体中文字幕。
- `evidence.json`：本次录制事件及最低可重复验证项。实际下载的 CSV 表含三条用例，实际下载的 XMind 的内容也包含人工修改标题。
- 成片、海报与字幕：站点 master `videos/portfolio/`。

在已安装 Node 24、Chrome、Python、FFmpeg 和 cwebp 的 Mac，将上述公开页面保存为 `app.html`。先执行 `node run.mjs` 快速实操验证；执行 `node run.mjs --record` 重新录制，最后执行 `python3 assemble.py` 合成。本脚本只使用临时浏览器配置和回环模型，不能传入外部模型地址。原始逐帧临时文件不纳入版本库。
