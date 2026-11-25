# 测试游记｜视频制作源文件

这里是文章讲解视频的可编辑 Remotion 工程，不是网站正文，也不是成片镜像。每个条目使用文章地址末尾的 ID；已发布的 MP4 继续由仓库的 Releases 提供。可直接使用随工程归档的普通话配音重新渲染，无需登录账户、联网配音或访问原文里的任何系统。

## 目录

- `episodes.json`：视频标题、文章 ID、帧率、已归档时间轴的帧数及渲染器。
- `episodes/<文章ID>/storyboard.json`：分镜、画面数据和旁白文本。旧首片的分镜从其最终时间轴整理。
- `episodes/<文章ID>/timeline.json`：Remotion 读入的时间轴，包含口播片段、帧位置和屏幕字幕。
- `episodes/<文章ID>/assets/`：按场景和句子拆分的实际配音 MP3；仅有片头画面的篇目包含对应无字插画。
- `episodes/<文章ID>/captions.vtt`：已发布的独立中文字幕。
- `renderers/`：原动态图解、SVG 和布局。首片分章节混合两版场景；Redis 第五章保留发布版的独立指标图。
- `tools/` 和 `package-lock.json`：渲染、检查与可选的配音重建工具。没有成片、生成日志、临时文件或网站正文。

## 安装、预览与导出

需要 Node.js 20+、Python 3.10+、本机 Chrome 或 Chromium，以及支持中文的字体（在原制片 Mac 上用苹方）。FFmpeg 和 ffprobe 用于媒体检查或可选的配音重建。包依赖安装需要 npm 注册表或本地缓存；工程不会在导出时下载图片、配音或浏览器。

```sh
npm ci
npm run check
npm run render -- --list
# 约三秒预览
npm run render -- wechat-2499cfc9d36cbb --frames 0-47
# 完整导出，默认 out/<文章ID>.mp4
npm run render -- wechat-2499cfc9d36cbb
```

找不到浏览器时用 `--browser "/path/to/chrome"`。不同操作系统、字体、FFmpeg/Chrome 或编码设置可能让导出的字形或媒体字节与原片有差异；源时间轴和实际发布版配音均保留。导出不会自动上传。

## 如何修改

- 微调画面或字幕：修改该条 `timeline.json` 的画面数据和对应的 `captions.vtt`；改通用的动画样式用 `renderers/`。注意字幕文本修改不会替换配音。
- 修改旁白或增删分镜：先改 `storyboard.json` 并备份原配音。安装 `python3 -m pip install -r requirements-voice.txt`，然后运行 `python3 tools/retime.py <文章ID> --apply`（需要联网和本机 FFmpeg）。此命令只用 Microsoft Edge TTS 晓晓普通话 `zh-CN-XiaoxiaoNeural`，服务失败时停止，不回退到其他声线；提交给服务的旁白必须只含可公开的内容。它会更新配音、字幕、时间轴和音色校验证据。已归档配音的本地重渲仍不需要联网。
- 演示手机号、密钥、口令、令牌或其他身份资料时，只能用合成值或占位符。不要把原始值放进分镜文件、图像、旁白、字幕或其它随工程公开的素材。

## 归档后续批次

对已经人工检查过的原生 16 fps 动画项目，导入脚本只接收四个明确指定的输入，并按时间轴筛选引用的 MP3 和可选片头图，不会复制源目录、原文、日志或其它资产。先做检查，再把 `--check-only` 换成 `--reviewed` 导入；新条目不会覆盖已有条目：

```sh
python3 tools/import_episode.py \
  --storyboard path/to/storyboard.json --timeline path/to/pilot-props.json \
  --assets path/to/audio --captions path/to/article.vtt --check-only
```

脚本只能检查文件结构和若干常见敏感格式，不能代替听看配音、图像和字幕。素材包含账户、身份或访问凭据时，须在进入工程之前用虚构值或占位符替换，不要只是给原值加模糊效果。
