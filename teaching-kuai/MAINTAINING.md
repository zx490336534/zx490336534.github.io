---
created: 2026-06-18
updated: 2026-06-18
---

# 课程维护说明

本文件给后续维护课程的人或 Agent 看。学习者直接从 `lessons/index.html` 开始，不需要读本文件。

## 当前课程入口

- 完整学习地图：`lessons/index.html`
- kuai-service（Java 后端）课程：`lessons/service/`
- kuai-service-front（Next.js 前端）课程：`lessons/front/`
- kuai-service-py（Python MCP）课程：`lessons/py/`
- 跨仓库专题（跨仓架构 / AI 测试概念 / 全栈实战 / 部署监控）：`lessons/` 根
- 概念速查：`reference/`（基础概念 + `internal-concepts.html` 平台内部概念）

所有 HTML 跳转使用相对路径，复制整个 `teaching-kuai/` 目录后仍可离线浏览。

## 课程定位

用户是新人，目标系统掌握 Kuai 测试平台三仓库，从全局认知到能独立参与开发。教学围绕 Kuai 真实代码补最小够用知识，不系统学通用 Java/Spring/React/Python 工程。

## 必须遵守的真实代码事实（2026-06-18 已核对本地仓库）

- **kuai-service**：Java 8 + pilot-boot-dependencies 2.3.9 + Spring Boot + MyBatis-Plus + tddl-min 5.3.3（MySQL via TDDL）+ spring-boot-starter-data-mongodb + Quartz 2.3.0；pom 含 postgresql 42.6.0 驱动（用途待核）；Jetty/8080。
- **kuai-service-front**：Next.js 16.1.1 + **React 18.2.0**（非 17/19）+ antd 6.1.3 + @reduxjs/toolkit 1.9.7 + langchain 1.4 + @langchain/langgraph 1.3 + @anthropic-ai/claude-agent-sdk 0.2.90 + **Tailwind 4.2.1 + shadcn + radix**（与 Ant Design 并存，不只 CSS Modules）+ langfuse 3.x；pnpm 管理。
- **kuai-service-py**：Python >=3.12 + **mcp[cli]==1.12.0** + FastAPI + sse-starlette + **langchain-openai + langchain-mcp-adapters + langgraph**（非纯 MCP）+ **chromadb>=1.3.5 向量库** + deepeval + aiomysql；uv 管理。
- 需求号：**HUXING-xxx**（Kaptain），非 COOAI-xxx。

## 新增或修改课程的规则

- 新课程按所属仓库放入 `lessons/service/`、`lessons/front/`、`lessons/py/`；跨仓库专题放 `lessons/` 根。
- 概念速查放 `reference/`，不要放回 `lessons/concepts/`（该目录已废弃）。
- 链接前缀规则（按当前文件位置）：
  - 同子目录课程互链：直接 `X.html`
  - 跨子目录：`../front/X.html`、`../service/X.html`、`../py/X.html`
  - 到 `lessons/` 根跨仓课：`../0013-*.html`
  - 到概念速查：`../../reference/X.html`（子目录内）/ `../reference/X.html`（根）
  - 到学习地图：`../index.html`（子目录内）/ `index.html`（根）
- 每节课底部导航保持三段：`← 上一课` ｜ `完整学习地图` ｜ `下一课 →`。
- 每节课要短、聚焦一个小胜利，并链接回学习地图。
- 引用源码用仓库相对路径，如 `kuai-service/src/main/java/...`，不要写个人机器绝对路径。
- 新增/更新后务必跑断链检查（见验证章节），保证零断链。

## 已知校准点与待办

- 前端 React 18 + Tailwind 4 已在 RESOURCES 钉死；课程 0034 若只提 CSS Modules，后续维护时可补充 Tailwind/shadcn 说明。
- 后端 Java 8（非高版本），讲 Spring 时注意不要套用 Java 17+ 语法。
- 待核：kuai-service pom 中 postgresql 42.6.0 驱动的实际用途（是否某模块连 PG）。
- 概念页待补：fetch-api、redux-basics、yaml-basics 在 `reference/` 暂无独立页（0028/0029 已改指向相近现存课）。

## 断链检查（验证）

```bash
# 收集所有内链，逐一确认目标存在
python3 - <<'PY'
import os,re
ROOT="/Users/zhongxin/myNote/teaching-kuai"
m={}
for dp,_,fs in os.walk(ROOT):
    for f in fs:
        if f.endswith('.html'): m[f]=1
bad=[]
for dp,_,fs in os.walk(ROOT):
    for f in fs:
        if not f.endswith('.html'):continue
        p=os.path.join(dp,f)
        for h in re.findall(r'href="([^"]+\.html)"',open(p,encoding='utf-8').read()):
            if h.startswith(('http://','https://','mailto:','//')):continue
            if os.path.basename(h) not in m: bad.append((os.path.relpath(p,ROOT),h))
print('断链数:',len(bad))
for b in bad:print(' ',b)
PY
```
