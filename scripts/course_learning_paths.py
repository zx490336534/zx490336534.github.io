"""Stage order and practical milestones; existing route keys stay stable."""

PATHS = {
    "teaching-aihom": (
        ("foundation", "跑通前后端", "从一次提交开始，逐步读懂 HTTP、请求取消与运行时数据。产出：一份带正常与失败分支的接口契约。",
         ("request", "http-payload", "abort", "runtime-contract", "ui-state")),
        ("engineering", "拆分服务与模型", "把业务判断和外部模型分开，收紧结构化输出与上下文边界。产出：一条不依赖真实模型的可测链路。",
         ("service", "structured-output", "context-isolation", "retrieval-grounding")),
        ("events", "还原流式与工具调用", "从完整事件帧读到断线恢复，再看 Agent 如何推进和调用工具。产出：能回放乱序、重复和缺失事件的用例。",
         ("stream-protocol", "stream", "agent", "tool")),
        ("data", "稳住状态与持久化", "把版本冲突、任务认领、通知发送和视图更新串起来。产出：一个能复现崩溃后恢复的实验。",
         ("atomic-publish", "durable-worker", "outbox", "views")),
        ("quality", "测试、观测与评测", "把代码走查变成可重复的测试，区分结果质量、延迟和系统故障。产出：一张定位问题的证据表。",
         ("test-layers", "diagnosis", "trace-metrics", "latency-budget", "layout-eval")),
        ("practice", "端到端实战", "用前面的机制完成一次功能演进，并准备基准、异常复现与回滚证据。",
         ("capstone", "multi-room-rollout")),
    ),
    "teaching-kuai": (
        ("foundation", "读懂一次测试运行", "先区分测试层次、数据、接口契约和看板。产出：能复现同一失败的一份运行记录。",
         ("job", "test-layers", "test-boundaries", "replay-fixtures", "parallel-fixtures", "contract", "dashboard")),
        ("engineering", "构建稳定的执行系统", "用重试、租约和取消应对任务争抢和执行失败。产出：任务调度状态图和故障边界测试。",
         ("schedule", "worker-retries", "worker-leases", "worker-cancel")),
        ("regression", "设计高信号回归", "让回归选对用例、定位偶发失败，再把生成结果送回可审查的测试流程。产出：带选择理由的回归用例。",
         ("test-selection", "flaky-tests", "generate")),
        ("evaluation", "评测答案与工具过程", "用固定的数据版本、公平的评分和可核对的动作轨迹度量 Agent。产出：能解释每次扣分的评测报告。",
         ("eval", "dataset-versioning", "rubrics", "model-grader", "trace-contract")),
        ("release", "建立可信发布门槛", "把监控、统计不确定性和报告证据合起来，学习怎么作出上线或暂停的决定。",
         ("observability", "gate-statistics", "evidence-report")),
        ("practice", "端到端实战", "给同一候选版本跑完整回归，用可追溯证据说明是否发布，并留下复跑步骤。",
         ("capstone", "graduation")),
    ),
}
