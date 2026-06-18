---
created: 2026-06-17
updated: 2026-06-17
---

# Mission: 打好 AIHom 全栈地基，最终能独立参与前后端开发

## Why
用户是测试工程师，当前目标升级为全栈参与公司的 AIHom 项目开发：既要读懂和修改后端 `ai-native-service` / `auto-layout-service`，也要理解前端 `ai-home` / `viewer-2d` / `render-3d` 的协作边界。之前直接冲 AIHom 实战发现地基不够、看不懂代码，所以先补 Spring AI 和 AIHom 全栈工程基础。学成后能从"测试别人写的代码"升级到"自己读懂、改动、新增 AIHom 的前后端功能"。

## Success looks like
- 能读懂 AIHom 后端（ai-native-service / auto-layout-service）里一段 Spring AI、Processor、配置或异步任务代码，并说清它在调用链里做了什么
- 能读懂 AIHom 前端（ai-home / viewer-2d / render-3d）里一段 React、状态管理、SDK/MCP、iframe/postMessage 或渲染状态代码，并说清它和后端如何协作
- 能独立新增一个 AIHom 小功能：确认需求 → 找到前后端改动边界 → 配置模型/接口/状态 → 写 ChatClient / ChatModel / Agent / React/StateManager 相关代码 → 接到接口或 UI 上
- 能把改动放进真实工程流程：根据 Kaptain 事项建分支、提 MR、理解 release/日期分支、做本地/环境联调、知道上线前后该看哪些日志和中间件
- 遇到 RAG、Tool Calling、会话记忆等进阶场景，知道选哪个 Spring AI 抽象、怎么落地
- 写出的代码能通过自己（测试工程师）的测试标准

## Constraints
- Java 基础很生疏（类 / 接口 / 注解 / 泛型 / 依赖注入都不熟），必须先补最小够用的地基，不能跳过
- 前端按"能介入 AIHom 开发"补最小够用地基：JavaScript 运行模型、TypeScript、浏览器/DOM/Network、React 17、CSS 布局、工程化调试、KAF/reactive-framework、agent-conversation-sdk、iframe/postMessage，不走 Next.js 路线
- 学习是跨 session 的长期过程，每节课要短、可快速完成、有小胜利
- 中文教学，案例尽量贴合 AIHom 真实场景
- 当前 Spring AI 社区版已到 2.x，但 AIHom 本地代码已核实使用 Spring AI `1.1.2` + Spring AI Alibaba `1.1.2.0.5-qh`；教学必须对齐 1.1.x + Alibaba，版本差异处对照标注

## Out of scope
- 不系统学 Java（只学读 / 写 AIHom 代码必需的最小子集）
- 不系统学 Spring 全家桶（只学 Spring AI 必需的 Spring Boot 子集）
- 不系统学通用前端工程（只学 AIHom 前端协作必需的 React/TS/状态/SDK/viewer 子集）
- 暂不追求成为 Spring 源码级专家

## 学习路径
```
阶段0  Java 够用就好（类 / 接口 / 注解 / 泛型 / lambda）
  ↓
阶段1  Spring Boot 够用就好（依赖注入 / 自动配置 / starter / 三层注解 / yml）
  ↓
阶段2  Spring AI 核心 ★重点（ChatClient / Prompt / 流式 / 结构化输出 / RAG / Tool / 会话记忆）
  ↓
阶段3  AIHom 后端工程地基（Maven 多模块 / Web 三层 / 配置 / 调试 / 异步任务）
  ↓
阶段4  工程运行与发布地基（后端/前端本地运行 / Coops Agent 配置 / 环境排查 / Git-Kaptain-release）
  ↓
阶段5  前端通用地基（JavaScript / TypeScript / 浏览器 / React 渲染 / CSS / 工程化调试）
  ↓
阶段6  AIHom 前端工程地基（React 17 / reactive-framework / SDK + MCP / viewer 集成）
  ↓
阶段7  回到 AIHom 全栈实战（这次能看懂、能改、能联调、能走发布流程）
```
