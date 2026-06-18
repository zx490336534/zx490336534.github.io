---
created: 2026-06-18
updated: 2026-06-18
---

# Mission: 系统掌握 Kuai 测试平台三仓库，能独立参与开发

## Why
用户是新人，目标是系统掌握酷家乐 AI 测试平台（Kuai）。Kuai 由三个仓库协同运转：`kuai-service`（Java 后端）、`kuai-service-front`（Next.js 前端）、`kuai-service-py`（Python MCP 服务）。需要从全局认知出发，先建立三仓库分工与数据流的整体地图，再逐仓库深入，最终能读懂、改动、新增跨三仓库的功能，并跑通本地开发与部署。

## Success looks like
- 能说清三仓库职责边界与数据流：前端如何发起 Agent 对话、如何经 MCP 调用工具、后端如何管理 Prompt/LLM 评估/知识库、Python 服务如何统一管理多协议 MCP Server
- 能逐仓库读懂一段代码并定位调用链：后端 Controller→Service→Mapper；前端 组件→Redux→LangChain Agent→MCP；Python FastAPI→MCP Server 生命周期
- 能按各仓库 dev-guide 本地跑起三个服务并完成联调
- 能新增一个小功能（一个新 Prompt / 一个新前端页面 / 一个新 MCP Server），打通前后端 + Python
- 能用 AI 测试视角理解 Kuai 核心能力：Prompt 版本管理、LLM 评估、知识库/分享应用、微信机器人
- 能把改动放进真实工程流程：基于 HUXING 需求建分支、提 MR、本地联调、理解部署与监控（Langfuse）

## Constraints
- 新人零基础起步，每节课短、可快速完成、有小胜利；不强求一次性学完
- 中文教学，案例贴合 Kuai 真实代码（HUXING-xxx 需求、Pilot 平台、toad 配置）
- 三仓库技术栈差异大，需分别补最小够用地基：Java 8 + Spring Boot + MyBatis-Plus + TDDL；Next.js 16 + React 18 + LangChain + Ant Design 6；Python 3.12 + FastAPI + MCP
- 优先学 Kuai 真实代码必需的子集，不系统学通用 Java/React/Python 工程

## Out of scope
- 不系统学 Java / Spring 全家桶（只学 kuai-service 必需子集）
- 不系统学通用前端工程（只学 kuai-service-front 必需的 Next.js/React/Redux/LangChain 子集）
- 不系统学 Python Web（只学 kuai-service-py 必需的 FastAPI/MCP 子集）
- 暂不追求任一框架的源码级精通

## 学习路径
```
阶段0  平台全局认知 ★起点
       （三仓库概览 + 跨仓架构 + AI 测试核心概念）
  ↓
阶段1  三仓库地基
       （每仓库：概览 → 架构 → API/数据 → dev-guide 本地运行）
  ↓
阶段2  核心功能深入
       service: Prompt / LLM评估 / 微信机器人 / 知识库 / 数据库
       front:   Agent / MCP / 状态 / 对话流式 / 组件 / API Routes / 认证 / 技能 / Claude Code / 测试 / HTTP / 导航 / Ant Design
       py:      MCP 服务架构 / 传输协议 / 服务器生命周期
  ↓
阶段3  全栈实战
       （全栈开发 + 部署监控 + 三仓库联调 + 真实 HUXING 任务）
```
