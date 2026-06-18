---
created: 2026-06-18
updated: 2026-06-18
---

# Kuai 学习资源

> 本工作区的高可信知识源。讲解与课程内容应从这里取材，而不是凭参数记忆臆测。
> 代码已于 2026-06-18 全部 `git pull` 到各仓库 master 最新。

## Knowledge（代码与文档）

### A. 核心工程清单（一手代码，最高可信）

> 源码仓库与 `myNote/` 同级放在 `../gitproject/<repo>`；课程引用代码统一用仓库相对路径，例如 `kuai-service/pom.xml`。master 快照为 2026-06-18 核实时点，以仓库 `git log` 实时为准。

**kuai-service — Java 后端（测试平台"大脑"）**
- GitLab: https://gitlab.example.com/test/bim/kuai-service
- 本地相对路径: `../gitproject/kuai-service`
- master 快照: `c4d36dc6`（2026-06-16，HUXING-17044）
- 结构: 单模块 Maven，`src/main/java/com/qunhe/kuai/{controller,Service,mapper,entity,config,...}` + `pom.xml` + `_appconfig/`
- 用途: Prompt 管理、LLM 评估、DeepEval、微信机器人、知识库/分享应用、导师路由、Know OpenAPI。后端学习起点。

**kuai-service-front — Next.js 前端（Agent-First）**
- GitLab: https://gitlab.example.com/test/bim/kuai-service-front
- 本地相对路径: `../gitproject/kuai-service-front`
- master 快照: `2b4e816`（2026-06-17；本地另有 `f0225f6` 教程暂存分支）
- 结构: `src/` + `next.config.js` + `package.json` + `_appconfig/`，pnpm workspace
- 用途: 对话 UI、LangChain Agent 系统、MCP 工具管理、Prompt 管理、技能系统、Claude Code 集成。

**kuai-service-py — Python MCP 服务（多协议网关）**
- GitLab: https://gitlab.example.com/test/bim/kuai-service-py
- 本地相对路径: `../gitproject/kuai-service-py`
- master 快照: `76a6742`（2026-06-15，HUXING-17292）
- 结构: `main.py` + `src/` + `libs/` + `pyproject.toml` + `uv.lock`
- 用途: MCP Server 管理平台，支持 SSE/Stdio/StreamableHTTP 多协议，统一 HTTP 接口管理多个 MCP 服务器；亦含 langchain/langgraph、chromadb 向量库、deepeval 评估。

### B. 三仓库技术栈（已从 pom.xml / package.json / pyproject.toml 核实，2026-06-18）

> 这些是开发 Kuai 前必须对齐的版本事实，不要套用网上通用教程的默认版本。

**kuai-service（后端）**
- **Java 8**（`<java.version>1.8</java.version>`）
- **Spring Boot**（版本由 parent `com.qunhe.middleware:pilot-boot-dependencies:2.3.9` 公司脚手架管理）
- MyBatis-Plus + 原生 MyBatis 注解（`@Select/@Insert` + `BaseMapper`）
- **tddl-min 5.3.3**（MySQL via TDDL 中间件）+ spring-boot-starter-data-mongodb
- postgresql 42.6.0 驱动（pom 中存在，具体用途待核）
- Quartz 2.3.0 + Spring Scheduling；spring-retry 1.3.4；Caffeine；Thymeleaf
- hunter-pilot-boot-starter 4.0.8（Pilot 平台接入）、soa integration 1.2.0、authnet-sso-client（SSO）
- Jetty / 8080

**kuai-service-front（前端）**
- **Next.js 16.1.1** + **React 18.2.0**（非 17/19）
- **antd 6.1.3** + @ant-design/icons；**Tailwind 4.2.1 + shadcn 3.8.5 + radix-ui + cmdk + lucide-react**（与 Ant Design 并存，不只 CSS Modules）
- @reduxjs/toolkit 1.9.7 + react-redux 9（会话 / 状态管理）
- langchain 1.4.0 + @langchain/{core 1.1.45, langgraph 1.3.0, anthropic, openai, community, mcp-adapters 1.1.3}
- @anthropic-ai/claude-agent-sdk 0.2.90（Claude Code 集成）
- ai（Vercel AI SDK）6.0.99 + @ai-sdk/{react,openai,langchain}；deepagents 1.9.0
- langfuse 3.38.6 + langfuse-langchain（可观测）；mongodb 7.0.0（会话持久化）
- echarts 6、streamdown、react-markdown 10 + shiki、driver.js、node-cron
- **pnpm** 管理

**kuai-service-py（Python）**
- **Python >=3.12**
- **mcp[cli]==1.12.0**（MCP SDK）+ sse-starlette（SSE）
- fastapi>=0.104.0 + uvicorn[standard] + pydantic 2
- **langchain-openai + langchain-mcp-adapters>=0.1.9 + langgraph>=0.6.5**（也用 LangChain 编排，非纯 MCP）
- **chromadb>=1.3.5**（向量库）、deepeval>=0.20.0（评估）、openai
- aiomysql（连 MySQL）、httpx、aiohttp
- **uv** 管理（uv.lock），源 aliyun + 群核 nexus

### C. 概念学习资料（框架认知）

- [Spring Boot 官方文档](https://docs.spring.io/spring-boot/) — 用：补 @RestController/@Service/DI/自动配置最小认知。
- [MyBatis-Plus 官方](https://baomidou.com/) — 用：Mapper/BaseMapper/条件构造器用法。
- [Next.js 官方文档（App Router）](https://nextjs.org/docs) — 用：Route Handlers、布局、数据获取，对齐 16.x。
- [LangChain JS 官方](https://js.langchain.com/) + [LangGraph JS](https://langchain-ai.github.io/langgraphjs/) — 用：Agent / Tool / createReactAgent / 流式，对齐 1.x。
- [Model Context Protocol 规范](https://modelcontextprotocol.io/) — 用：MCP 协议、传输方式（SSE/Stdio/StreamableHTTP）、Server/Tool。
- [FastAPI 官方](https://fastapi.tiangolo.com/) — 用：路由、依赖注入、async、Pydantic。
- [Ant Design 6](https://ant.design/) + [Ant Design X](https://x.ant.design/) — 用：组件、AI 组件。
- [Anthropic Claude Agent SDK (TS)](https://github.com/anthropics/claude-agent-sdk-typescript) — 用：代码分析、Agent 调用、超时处理。
- [Langfuse 文档](https://langfuse.com/) — 用：LLM 可观测、Trace、评估。

### D. 内部基础设施

- Pilot 平台：启动参数在 `_appconfig/cicd.yml`，参考 [Pilot 文档](http://manual.k8s-new.example.com/pilot/1.0.0/)。用：本地运行、环境配置、多数据源。
- toad：环境差异化配置。
- Kaptain（kaptain.example.com）：敏捷需求，**HUXING-xxx** 系列。用：把代码改动对应到需求背景。
- Coops / Coohom AI Native 体系：与 AIHom 共用的 Agent / MCP / Pilot 基础设施。

## Wisdom（团队与协作入口）

- **GitLab MR 评审** — 各仓 Merge Request 评论是了解"为什么这么改"的一手 wisdom。用：看近期 HUXING 合入讨论。
- **Confluence**（cf.example.com）— 架构 / Dev Design。用：补全代码看不出的设计意图。
- **Kaptain**（kaptain.example.com）— HUXING 需求背景。
- LangChain / MCP 社区实践与官方示例。

## Gaps（待补）

- ✅ 2026-06-18：完成顶层治理闭环（MISSION/RESOURCES/NOTES/MAINTAINING）+ 概念速查提升为 `reference/` + 目录按仓库重构（service/front/py）+ 修复全部已有断链。
- ⚠️ 待核：kuai-service pom 中 `postgresql 42.6.0` 驱动的实际用途。
- ⚠️ 课程校准待跟进：前端 React 18 + Tailwind 4/shadcn（0034 曾只提 CSS Modules）；Python 服务 langchain/langgraph + chromadb 在 0010/0011 可补充。
- ⚠️ 概念页待补：`reference/` 暂无 fetch-api、redux-basics、yaml-basics 独立页（相关课程已改指向相近现存课）。

## 同步状态备注

- 2026-06-18：三仓库核对到 master 最新（kuai-service `c4d36dc6`、kuai-service-front `2b4e816`、kuai-service-py `76a6742`）。
- 2026-06-18：目录重构为 `lessons/{service,front,py}` + 顶层 `reference/`，全部内链用 relpath 重算并通过断链校验。
