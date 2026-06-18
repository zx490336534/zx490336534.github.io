---
created: 2026-06-18
updated: 2026-06-18
---

# Notes

- 用户偏好：中文教学
- 身份：新人，零基础系统学 Kuai 测试平台
- 学习策略：够用导向，先全局后深入，每课聚焦一个小胜利
- 目录约定（2026-06-18 重构后）：
  - `reference/` — 概念速查（由 `lessons/concepts/` 提升），含 11 个基础概念 + `internal-concepts.html`（平台内部概念）
  - `lessons/index.html` — 完整学习地图（学习路径为主视图）
  - `lessons/service/` — kuai-service（Java 后端）课程
  - `lessons/front/` — kuai-service-front（Next.js 前端）课程
  - `lessons/py/` — kuai-service-py（Python MCP）课程
  - `lessons/` 根 — 跨仓库专题（0013 跨仓架构 / 0014 AI 测试概念 / 0015 全栈实战 / 0027 部署监控）
- **Kuai 真实栈（RESOURCES.md 已核实，2026-06-18）**：
  - 后端 kuai-service：**Java 8** + pilot-boot-dependencies 2.3.9 + Spring Boot + MyBatis-Plus + TDDL(tddl-min 5.3.3) + MongoDB + Quartz；Jetty/8080
  - 前端 kuai-service-front：**Next.js 16** + **React 18** + Ant Design 6 + Redux Toolkit 1.9.7 + **LangChain 1.4 / LangGraph** + claude-agent-sdk 0.2.90 + **Tailwind 4 + shadcn**（与 Ant Design 并存）+ langfuse；pnpm 管理
  - Python kuai-service-py：**Python 3.12** + **mcp[cli] 1.12.0** + FastAPI + **langchain/langgraph** + chromadb 向量库 + deepeval + aiomysql；uv 管理
- ⚠️ 后端是 **Java 8**（非高版本）；前端是 **React 18 + Tailwind 4**（课程曾只提 CSS Modules，已校准）；Python 服务也用 langchain/langgraph + chromadb（非纯 MCP）
- 需求号体系：**HUXING-xxx**（Kaptain），不同于 AIHom 的 COOAI-xxx
- 链接规范：子目录内课程互链用相对路径（同级无前缀、跨目录 `../front/X.html`、到 reference 用 `../../reference/X.html`、到 index 用 `../index.html`）
