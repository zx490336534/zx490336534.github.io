---
created: 2026-06-17
updated: 2026-06-17
---

# AIHom 学习资源

> 本工作区的高可信知识源。讲解与课程内容应从这里取材，而不是凭参数记忆臆测。
> 代码已于 2026-06-17 全部 `git pull` 到各仓库 master 最新。

## Knowledge（代码与文档）

### A. 核心工程清单（一手代码，最高可信）

> 源码仓库默认与 `myNote/` 同级放在 `../gitproject/<repo>`；课程正文引用代码时统一使用仓库相对路径，例如 `ai-native-service/pom.xml`。「master 快照」为 2026-06-17 更新时提交，仅参照，以仓库 `git log` 实时为准。

**后端（Java 21 / Spring Boot 3 + Spring AI Alibaba）**

- **ai-native-service** — AI 对话与 Agent 编排核心
  - GitLab: https://gitlab.example.com/i18n/backend/ai-native-service
  - 本地相对路径: `../gitproject/ai-native-service`
  - 结构: `common`(Java8) + `client`(Java8) + `web`(Java21，开发主战场) + 多模块 `pom.xml`
  - master 快照: `a26ceab`（release/20260611 合入）— 含图像生成带素材库 `ImageGenerateWithStockProcessor`、多消息(COOAI-446)等
  - 用途: 消息流/WebSocket、StateGraph、Agent/Supervisor、Tool/MCP 桥接都在此。学习起点。

- **auto-layout-service** — AI 布局/户型生成
  - GitLab: https://gitlab.example.com/i18n/backend/auto-layout-service
  - 本地相对路径: `../gitproject/auto-layout-service`
  - 结构: `common` + `client` + `web` + `doc/` + `spec/` + `docs/`
  - master 快照: `32fe7dd5`（release/20260611 合入）— 含信用体系 v2 (COOAI-217)
  - 用途: 异步 Processor 模式（`BaseAsyncProcessor`）、布局任务生命周期。

**前端**

- **ai-home** — 主前端（React 17 + Rspack + KAF/reactive-framework）
  - GitLab: https://gitlab.example.com/i18n-fe/bim/ai-home/ai-home
  - 本地相对路径: `../gitproject/ai-home`
  - master 快照: `33a415e0`（release/20260616 合入）— 含 changeAPI (COOAI-424/453)
  - 用途: 对话 UI、与后端 WebSocket 通信、MCP Tool 前端执行侧。

- **viewer-2d** — 2D 户型/平面查看器（PixiJS）
  - GitLab: https://gitlab.example.com/i18n-fe/bim/ai-home/viewer-2d
  - 本地相对路径: `../gitproject/viewer-2d`
  - master 快照: `610619e`（release/20260528 合入，COOAI-318）
  - 用途: 2D 渲染引擎（Scene2D/PixiJS）、实体系统、Drawable 绑定、交互。

- **render-3d** — 3D 渲染与离线出图
  - GitLab: https://gitlab.example.com/i18n-fe/bim/ai-home/render-3d
  - 本地相对路径: `../gitproject/render-3d`
  - master 快照: `f1990b9`（release/20260602 合入，COOAI-384 修复）
  - 用途: 3D 场景渲染、离线渲染任务管线、SnapshotTaskStatus 状态机。

### B. 后端框架栈（已从 ai-native-service 父 pom 核实，2026-06-17）

> 这些是开发 ai-native-service 前必须对齐的版本事实，不要套用网上 Spring AI 2.x 教程。

- **Java 21** + **Spring Boot 3**（用 `*-spring-boot3-starter`、Jetty 容器，非 Tomcat）
- **Spring AI `1.1.2`**（注意：不是 2.x；查文档应对齐 1.1.x）
- **Spring AI Alibaba `1.1.2.0.5-qh`** — 群核（Coohom）定制版，Agent 编排的核心
  - 关键依赖: `spring-ai-alibaba-agent-framework`（Agent 框架）、`spring-ai-alibaba-autoconfigure-dashscope`（模型走 **DashScope / 通义千问**）、`spring-ai-alibaba-starter-config-nacos`（Nacos 动态配置）
- **MCP**: `spring-ai-starter-mcp-server-webmvc`（后端作 MCP Server，通过 WebSocket 把 Tool 委托给前端执行）

### C. Spring AI / Spring Boot 学习资料（框架认知）

- [Spring AI 官方参考文档](https://docs.spring.io/spring-ai/reference/index.html) — 一手资料。**用: 查 ChatClient/Prompt/RAG/Tool 概念时，对齐 1.1.x 版本用法**（项目非 2.x）。
- [Spring AI Alibaba 官方文档](https://java2ai.com/) — **项目实际用的框架**，优先于此。用: Agent 框架、DashScope 接入、Graph/StateGraph 用法。
- [GitHub: alibaba/spring-ai-alibaba](https://github.com/alibaba/spring-ai-alibaba) — 源码与示例。用: 看官方 Graph/Agent 写法。
- [Spring 官方指南: RESTful Web Service](https://spring.io/guides/gs/rest-service) — 补 @RestController/@Service/DI 最小认知。
- [Baeldung — Spring Boot](https://www.baeldung.com/spring-boot) — 具体注解不懂时查。

### D. 内部基础设施（Pilot 平台，后端两仓 README 共同指向）

- [Pilot 官方文档](http://manual.k8s-new.example.com/pilot/1.0.0/) — 启动参数在 `/_appConfig/cicd.yml`。用: 本地运行、环境配置、多数据源。
- [Pilot 公共 API](http://manual.k8s-new.example.com/pilot/1.0.0/pilot-common-api) — 获取部署环境信息。
- [Pilot OPS](https://coops.example.com/pilot#/ops) — 查看中间件版本。
- 配置分工: 环境差异化 → **toad**；Agent 配置 → **Nacos**（动态更新）；状态图配置 → **MySQL**。

### D2. Coops Agent / MCP / Skill 配置资料

- [Coops Agent 管理中心帮助](https://cf.example.com/pages/viewpage.action?pageId=81421024361) — 用: 理解 Agent、Prompt、Model、MCP Server、Skill 配置入口，配置热更新、环境流转和发布导出能力。
- [Confluence: Tool 加载机制](https://cf.example.com/pages/viewpage.action?pageId=81477962780) — 用: 理解 `CustomNacosReactAgentBuilder` 如何加载 Agent/Prompt/Model/MCP Server，`ToolDefinition` 如何变成模型可见的 tools。
- [Confluence: MCP/SKILL 对外开放使用手册](https://cf.example.com/pages/viewpage.action?pageId=81467087582) — 用: 理解 Coops MCP/Skill 中心、MCP Server 对外开放、Token 与网关边界。
- 本地参考：AI Home Agent 架构查看逻辑 — 用: 理解 `graph_ai_home`、`state_graph`、`graph_nodes`、Nacos agent/prompt 配置之间的对应关系。
- 代码 `ai-native-service/ai-native-service-web/src/main/java/com/qunhe/i18n/ainative/service/web/agent/CustomNacosReactAgentBuilder.java` — 用: Nacos Agent 构建和 MCP tools 汇总入口。
- 代码 `ai-native-service/ai-native-service-web/src/main/java/com/qunhe/i18n/ainative/service/web/agent/CustomNacosMcpGatewayToolsInitializer.java` — 用: MCP Server detail、toolSpec、whiteTools、enabled 和 postmessage 协议处理。

### E. Git / 发布 / 上线流程资料

- [Confluence: Git Worktree 使用教程](https://cf.example.com/pages/viewpage.action?pageId=81475130844) — 用: 多任务、hotfix、review、release 分支并行验证，避免频繁 stash。
- [Confluence: Git 插件与发布分支自动创建脚本实践](https://cf.example.com/pages/viewpage.action?pageId=81250496209) — 用: 理解内部常见的 `release/YYYYmmdd` 日期发布分支。
- [Confluence: Git Release分支回滚流程规范](https://cf.example.com/pages/viewpage.action?pageId=80680447836) — 用: 理解 GitLab Revert、配置开关屏蔽、cherry-pick 重建分支的回滚顺序。
- 本地笔记 `4-归档/资源/技术/工具链/Git/Git基础知识(七)--分支开发工作流.md` — 用: 补 Gitflow、Feature、Release、Hotfix 分支通用概念。

## Wisdom（团队与协作入口）

内部无公开社区，以下是 AIHom 开发相关的协作场域：

- **GitLab MR 评审** — 各仓 Merge Request 评论是了解"为什么这么改"的第一手 wisdom。用: 看近期 release 合入（20260611/20260616）讨论。
- **Confluence** (cf.example.com) — 架构 / Dev Design。用: 补全代码看不出的设计意图。
- **Kaptain** (kaptain.example.com) — 敏捷需求（COOAI-xxx 系列）。用: 把代码改动对应到需求背景。
- [Spring AI Alibaba GitHub Discussions / 社区实践](https://github.com/alibaba/spring-ai-alibaba) — 框架踩坑与最佳实践。

## Gaps（待补）

- ✅ 已补齐全局学习地图：`lessons/index.html` 可快速跳转所有 HTML 课程；Spring AI 已融入完整学习地图，不再保留独立首页。
- ✅ 已修复所有课程 HTML 的本地断链，并在每个课程页底部追加统一的「完整学习地图 / 上一课 / 下一课」导航。
- ✅ 已新增 `reference/internal-concepts.html`，汇总 AIHom 公司内部概念、Confluence 与本地笔记来源。
- ✅ 已补充后端本地运行/部署、前端本地运行/部署、Coops Agent 配置与 MCP 注入、端到端环境排查、Git/Kaptain/release 发布流程课程。
- ✅ 已在 `reference/internal-concepts.html` 中补充部署运行命令、Coops Agent 配置与 MCP 注入、Git/Kaptain 发布分支速查。
- ⚠️ spring-ai-alibaba `1.1.2.0.5-qh` 为群核定制版，与社区版存在差异；遇到不符社区文档的行为，优先看仓库内 `*-qh` 改动。

## 同步状态备注

- 2026-06-17：核心仓库全部 `fetch + checkout master + pull --ff-only` 到 `origin/master` 一致。
  - ai-native-service、auto-layout-service 原在 release 分支，已切回 master；本地未跟踪工具文件（`.agents/`、`.claude/`、`AGENTS.md` 等）与 ai-native-service 的 `.mcp.json` 改动均已保留，无丢失。
- 2026-06-17：新增完整学习地图 `lessons/index.html`，并修复课程 HTML 本地跳转；每个课程页底部都有统一快速导航。
- 2026-06-17：对照核心工程真实代码校准课程内容；修正 ai-home 非 Next.js、WebSocket/STOMP 帧 + `RawSocketMessage` 业务体、`ChatClient` 与 `ChatModelFactory` / `ChatModel` 的边界，以及 `OpenAiChatModel` 作为 OpenAI-compatible 适配层的说明。
- 2026-06-17：按全栈目标新增 AIHom 介入开发前基础课 0028-0037，覆盖 Maven 多模块、Spring Web 三层、配置/Nacos、日志 trace、TypeScript/React、reactive-framework、SDK + MCP、viewer 集成、异步任务和跨仓开发工作流。
- 2026-06-17：补充前端通用地基课 0038-0043，覆盖 JavaScript 运行模型、TypeScript 类型系统、浏览器/DOM/Network、React 渲染模型、CSS 布局、前端工程化调试与测试。
- 2026-06-17：重构完整学习地图 `lessons/index.html`，改为“基础 → 进阶 → 深入 → 实战”的统一课程体系，不再使用旧版/主线/支线等来源分类。
- 2026-06-17：目录结构收敛到 `lessons/`：完整学习地图为 `lessons/index.html`，AIHom 全栈课程在 `lessons/aihom/`，Spring AI 地基课程在 `lessons/spring-ai/`；HTML 跳转统一使用相对路径，便于复制给其他人离线浏览。
- 2026-06-17：将过程性的中间记录压缩整理为 `MAINTAINING.md`，对外课程包不再暴露零散过程文件。
- 2026-06-17：新增工程运行与发布相关课程 0049-0053，覆盖后端运行部署、前端运行部署、Coops Agent 配置与 MCP 注入、端到端环境排查、Git/Kaptain/release 分支流程；学习地图扩展为 65 节。
