---
created: 2026-06-17
updated: 2026-06-17
---

# 课程维护说明

这个文件保留给后续维护课程的人或 Agent 看。学习者直接从 `lessons/index.html` 开始即可，不需要阅读本文件。

## 当前课程入口

- 完整学习地图：`lessons/index.html`
- AIHom 全栈课程：`lessons/aihom/`
- Spring AI 地基课程：`lessons/spring-ai/`（已融入完整学习地图，不保留独立首页）
- 公司内部概念速查：`reference/internal-concepts.html`

所有 HTML 跳转都应使用相对路径，确保复制整个 `teaching-aihom/` 目录后仍能离线浏览。

## 课程定位

用户目标是从测试工程师视角补齐 AIHom 全栈开发地基，最终能读懂、修改和联调 AIHom 的前后端功能。

教学路线不是系统学习 Java、Spring 或前端，而是围绕 AIHom 真实代码补最小够用知识：

- Java / Spring Boot 最小地基
- Spring AI + Spring AI Alibaba 核心
- AIHom 后端工程地基
- JavaScript / TypeScript / React / CSS / 浏览器调试地基
- ai-home / viewer-2d / render-3d 协作机制
- 工程运行与发布地基（后端本地运行、前端本地运行、Pilot/toad、pub deploy、Coops Agent 配置、Git/Kaptain/release 分支）
- 多仓联调和真实开发任务

## 必须遵守的真实代码事实

课程内容以核心本地仓库当前代码为准：

- `ai-native-service`
- `auto-layout-service`
- `ai-home`
- `viewer-2d`
- `render-3d`

已核实的关键事实：

- AIHom 后端核心是 Java 21 + Spring Boot 3 + Spring AI `1.1.2` + Spring AI Alibaba `1.1.2.0.5-qh`。
- AIHom 使用的是 Spring AI Alibaba 的 Agent / StateGraph / Graph / DashScope / MCP，不应按纯 Spring AI 或 Spring AI 2.x 教程来讲。
- `ai-home` 是 React 17 + TypeScript 4.7 + Rspack + KAF/reactive-framework，不是 Next.js。
- WebSocket 业务消息体以 `RawSocketMessage` / `ProcessorMessageType` 为核心，不是简单的 Spring `@MessageMapping` 控制器模型。
- 学 Spring AI 时可以用 `ChatClient` 建立心智模型，但讲 AIHom 实战时必须回到真实链路：Nacos 配置 -> `ChatModelFactory` / `ChatModel` -> Agent / StateGraph -> Tool / MCP / WebSocket。

## 新增或修改课程的规则

- 新课程优先放入 `lessons/aihom/`；只有明确属于 Spring AI 地基时才放入 `lessons/spring-ai/`。
- 更新 `lessons/index.html` 时，只按学习顺序归入“基础 / 进阶 / 深入 / 实战”，不要再按“旧课 / 新课 / 主线 / 支线”分类。
- 每节课要短、聚焦一个小胜利，并能链接回完整学习地图。
- 前端课程不能只讲项目 API，必要时先补 JavaScript、TypeScript、浏览器、React、CSS 和调试基础。
- 后端课程不要套用 Spring AI 2.x 内容；版本差异必须标注。
- 引用源码文件时使用仓库相对路径，例如 `ai-native-service/pom.xml`，不要写个人机器绝对路径。
- Git/Kaptain/release 发布课程只能讲可证实的通用流程；具体团队发布窗口、分支命名、MR 目标分支和上线平台动作必须以当期团队约定为准。

## 已移除的过程记录

原 `learning-records/` 目录主要是生成课程过程中的中间决策记录。对学习者价值很低，已将有用信息压缩进本文件，并移除该目录，避免课程包对外分发时显得混乱。
