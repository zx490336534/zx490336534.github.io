"""New public RoomLab chapters with independently executable examples."""
from textwrap import dedent

ROOMLAB_EXTRA = {}

def add(key, title, minutes, goal, scene, steps, exercise, quiz, term,
        question, flow, analysis, snippet, faults, assertions, recap, language="python"):
    prompt, options, correct, explanation = quiz
    snippet = dedent(snippet).strip()
    lesson = (key, title, minutes, goal, scene, steps, snippet.splitlines()[0],
              exercise, prompt, options, correct, explanation)
    depth = (question, flow, analysis, language, snippet, faults, assertions, recap)
    ROOMLAB_EXTRA[key] = (lesson, term, depth)

add("http-payload", "读懂一次生成请求的 HTTP 与 JSON", 16,
    "从请求方法、响应码、响应体三个位置判断下一步。",
    "RoomLab 提交布局生成。你在浏览器的网络面板看到 202，但返回体可能因为中间层故障而不完整。",
    ["先辨认发出的是创建任务，不是读布局。", "分开读 HTTP 状态和 JSON 字段。", "接受以后用任务编号追踪进展。"],
    "对照 202 有编号、202 无编号和 422 三条记录，写下每条下一步。",
    ("202 响应里没有任务编号，可以显示排队成功吗？", ["可以，只看状态码", "不行，回执契约不完整"], 1, "页面无法关联后续结果。"),
    ("响应契约", "除了状态码，还规定必要的字段和字段类型。"),
    "怎样从网络面板判断服务器真的受理了本次操作？",
    ["找创建任务的请求。", "核对状态码。", "读取媒介类型、JSON 与任务身份。", "把可追踪回执交给 UI。"],
    [("202 表示接受而非完成", "创建任务受到接受后通常还有排队、执行与校验。浏览器保留上一个布局，不把 202 当成可渲染结果。"),
     ("格式正确也可能不符合契约", "从 body 解出对象仍要检查任务编号是否为非空文本。一个成功码配上代理返回的 HTML 不能拿去订阅任务。"),
     ("拒绝输入和协议故障分开", "422 指向输入，格式错误指向响应链路；它们需要不同的提示。时间敏感的服务规范应另行注明。")],
    '''
    import json

    def receipt(status, media_type, body):
        if status == 422:
            return ("fix-input", None)
        if status != 202:
            return ("unexpected-status", None)
        if media_type.split(";")[0].strip().lower() != "application/json":
            return ("bad-media-type", None)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return ("bad-json", None)
        if not isinstance(payload, dict):
            return ("bad-receipt", None)
        task = payload.get("task")
        if not isinstance(task, str) or not task.strip():
            return ("bad-receipt", None)
        return ("wait", task)

    assert receipt(202, "application/json; charset=utf-8", '{"task":"R2"}') == ("wait", "R2")
    assert receipt(202, "application/json", '{}') == ("bad-receipt", None)
    assert receipt(202, "text/html", '<p>Oops</p>')[0] == "bad-media-type"
    assert receipt(422, "application/json", '{}')[0] == "fix-input"
    ''',
    [("状态码看着正常", "202 但缺失 task。", "不订阅、不显示已排队。"), ("返回 HTML", "媒体类型为 text/html。", "提示回执异常，别重误判成输入错。")],
    ["202 有效回执进入等待，不进入完成。", "缺身份和媒体类型异常能区分。", "422 显示修正输入的提示。"],
    "请求状态回答是否受理；回执身份让你知道在等哪一次。")

add("abort", "取消请求与防止旧结果覆盖", 19,
    "同时处理真正的取消和没有被及时取消的迟到响应。",
    "用户连续点两个房间。第一次任务的最慢回调可能在页面切换后仍执行。",
    ["新任务开始时取消旧请求。", "捕获本地选择的递增令牌。", "任何结果写入前核验令牌。"],
    "让第一次 Promise 忽略 AbortSignal，观察它完成后 UI 是否仍显示第二次结果。",
    ("有 AbortController 就能省掉回调归属检查吗？", ["可以", "不能"], 1, "取消只是通知，适配层可能未及时终止。"),
    ("AbortSignal", "向异步工作传达取消的对象，而非保证远端已经撤销。"),
    "为什么已经取消了请求，UI 还是可能恢复到旧选择？",
    ["显示新选择。", "通知旧读取停止。", "等待当前异步工作。", "仅当前令牌允许写 UI。"],
    [("取消的作用范围", "AbortController 控制支持该信号的工作。服务已经启动的任务不一定停止，生成按钮的取消语义应单独设计。"),
     ("双重保护", "取消减少无用工作，代际令牌约束结果能否提交。某些非 fetch 处理器忽略信号时，令牌仍然保护页面。"),
     ("错误也要判归属", "旧请求抛错不能覆盖当前请求的成功提示。示例捕获拒绝后同样检查令牌。")],
    '''
    const assert = require("node:assert/strict");
    let generation = 0, controller, shown;
    function deferred() {
      let resolve;
      const promise = new Promise(done => { resolve = done; });
      return { promise, resolve };
    }
    async function restart(fetchLayout) {
      controller?.abort();
      controller = new AbortController();
      const token = ++generation;
      try {
        const value = await fetchLayout(controller.signal);
        if (token === generation) shown = value;
      } catch (error) {
        if (token === generation && error.name !== "AbortError") shown = "error";
      }
    }
    (async () => {
      const a = deferred(), b = deferred();
      let oldSignal;
      const p = restart(signal => { oldSignal = signal; return a.promise; });
      const q = restart(() => b.promise);
      assert.equal(oldSignal.aborted, true);
      b.resolve("second");
      await q;
      a.resolve("first");
      await p;
      assert.equal(shown, "second");
    })().catch(error => { console.error(error); process.exitCode = 1; });
    ''',
    [("旧处理器不认取消", "第一次请求仍成功返回。", "输出还是第二次。"), ("旧请求迟到报错", "第二次成功以后第一次拒绝。", "不要覆盖当前成功状态。")],
    ["重新开始后旧信号是 aborted。", "忽略信号的旧结果也不能提交。", "旧失败和旧成功同样不能覆盖当前代。"],
    "把取消理解为节省资源，把令牌理解为拒绝错误写入。", "javascript")

add("runtime-contract", "类型声明不够：校验网络里的 unknown", 18,
    "在边界验证布局数据，再把它交给业务代码。",
    "接口曾返回数字 revision，偶尔也返回字符串。二维画法接受了，三维走另一条分支，页面显示不一致。",
    ["把网络解析结果当未知。", "检查根对象、数组和每一项。", "只把规范化的结果交给投影。"],
    "分别在 revision、x、id 注入异常，从报错路径定位是哪个字段。",
    ("JSON.parse 成功后可以直接当成布局吗？", ["可以", "还要校验结构"], 1, "可解析的 JSON 未承诺业务字段。"),
    ("unknown", "类型安全的边界输入；缩小类型之前不使用它的属性。"),
    "类型系统能保证这台服务返回的 JSON 与声明完全一致吗？",
    ["接收外部数据。", "检查每个必要字段与取值。", "按错误路径返回诊断。", "成功后复制成内部形状。"],
    [("编译期与运行时分工", "TypeScript 的类型断言只影响静态检查，不会修正外部字节。示例用 JavaScript 运行时检查演示同一个边界。"),
     ("别默认自动修复", "把字符串坐标强制转数字可能掩盖上游变更。需要兼容时应定义版本或明确转换规则，而不是让不同调用者自行猜。"),
     ("错误路径比整段响应有用", "端上提示出错字段位置，测试就能区分非法序号、异常数组和重复标识。生成后的几何约束仍应由规范验证。")],
    '''
    const assert = require("node:assert/strict");
    const bad = path => ({ ok: false, path });
    function readLayout(raw) {
      if (!raw || typeof raw !== "object") return bad("$");
      if (!Number.isSafeInteger(raw.revision) || raw.revision <= 0) return bad("revision");
      if (!Array.isArray(raw.items)) return bad("items");
      const used = new Set();
      const items = [];
      for (const [i, item] of raw.items.entries()) {
        if (!item || typeof item.id !== "string" || !item.id.trim() || used.has(item.id)) {
          return bad(`items[${i}].id`);
        }
        if (typeof item.x !== "number" || !Number.isFinite(item.x)) return bad(`items[${i}].x`);
        used.add(item.id);
        items.push({ id: item.id, x: item.x });
      }
      return { ok: true, value: { revision: raw.revision, items } };
    }
    const chair = { id: "chair", x: 1 };
    assert.equal(readLayout({ revision: "3", items: [] }).path, "revision");
    assert.equal(readLayout({ revision: 3, items: [chair, chair] }).path, "items[1].id");
    assert.equal(readLayout({ revision: 3, items: [{ ...chair, x: NaN }] }).path, "items[0].x");
    assert.deepEqual(readLayout({ revision: 3, items: [chair] }).value, { revision: 3, items: [chair] });
    ''',
    [("字符串版号", '传入 "3" 代替 3。', "返回 revision 路径。"), ("两物件同 ID", "同一数组加入两个 chair。", "第二项失败，不让联动身份发生歧义。")],
    ["合法输入生成可消费的布局模型。", "重复标识导致明确的断言。", "非法值不被隐式修正。"],
    "把不可靠的数据拦在两张图之前。", "javascript")

add("atomic-publish", "一条条件更新保护两个并发编辑", 23,
    "看懂版本比较为何要和更新一起发生。",
    "两个人从版本 2 开始编辑。两次保存都先读取到 2；如果比较和写入分开，后到一方会覆盖更早发布。",
    ["为编辑保留基础版本。", "用一条条件更新比较基础版本并写入。", "把零行更新当冲突而非成功。"],
    "从同一版本发起两次发布，第二次收到冲突以后重新读取。",
    ("保存前先查询版本，之后无条件写入安全吗？", ["安全", "不安全"], 1, "查询与写入之间状态仍可变化。"),
    ("比较并交换", "只在数据仍和预期相符时更新。"),
    "两个浏览器都显示版本 2，谁有权把结果写成版本 3？",
    ["读取基线版本。", "写入时同时验证房间和原版本。", "读受影响行数。", "返回已写或冲突。"],
    [("前端版本是条件，不是结论", "两个客户端的基线可以完全相同。数据库里的当前版本才决定一次发布是否可以成功。"),
     ("比较与替换合成一步", "示例用参数化 SQL 在同一条 UPDATE 里比较 room 与 revision，并同步修改数据和版号。单条语句证明原子条件；涉及多表时需要额外事务设计。"),
     ("不要自动静默合并", "冲突并不是网络超时，重试前需要重新读新版本并决定放弃、合并或重新编辑。返回版本差异比连续自动写有用。")],
    '''
    import sqlite3
    db = sqlite3.connect(":memory:")
    with db:
        db.execute("CREATE TABLE layout(room TEXT PRIMARY KEY, revision INT, shape TEXT)")
        db.execute("INSERT INTO layout VALUES (?, ?, ?)", ("room-A", 2, "initial"))

    def try_publish(room, base, shape):
        with db:
            changed = db.execute(
                "UPDATE layout SET revision = revision + 1, shape = ? "
                "WHERE room = ? AND revision = ?", (shape, room, base)
            ).rowcount
        return "written" if changed == 1 else "conflict-or-missing"

    def read(room):
        return db.execute(
            "SELECT revision, shape FROM layout WHERE room = ?", (room,)
        ).fetchone()

    baseline_a, baseline_b = read("room-A")[0], read("room-A")[0]
    assert try_publish("room-A", baseline_a, "chair") == "written"
    assert try_publish("room-A", baseline_b, "desk") == "conflict-or-missing"
    assert try_publish("room-B", 3, "unknown") == "conflict-or-missing"
    assert read("room-A") == (3, "chair")
    ''',
    [("两个编辑器相同基线", "A 写成功后 B 用旧版保存。", "B 返回冲突，A 的结果不变。"), ("写不存在房间", "提供没有记录的房间。", "不新建，不返回写成功。")],
    ["只有第一次更新成功。", "后写没有额外增加版号。", "保存内容与更新后的版本属于同一条记录。"],
    "有并发时，判断和写入必须作为一次不可分割的更新。")

add("test-layers", "一条布局需求如何拆成三层测试", 22,
    "区分组件输入、接口契约与集成链路，让失败定位到具体边界。",
    "要测试「超时保留旧布局」。只写一条端到端会发现退化，却未必知道坏在 UI 状态、回执格式还是保存。",
    ["把规则拆成三个可观测边界。", "每层注入能控制的故障。", "底层过了以后用一条窄集成覆盖链路。"],
    "故意把错误码改成其他值，看最先能指出原因的测试是哪条。",
    ("每一种输入组合都该用端到端测试吗？", ["应该", "边界值优先让快速小测试覆盖"], 1, "大测试只保留少数关键跨边界行为。"),
    ("契约测试", "约束输入、输出及错误形状，保证两端对同一边界有相同理解。"),
    "失败时怎样一眼看出是前端逻辑、响应形状还是接线问题？",
    ["纯 UI 接受各状态。", "接口返回约定字段。", "组合调用保留旧布局。", "用错误路径定位负责层。"],
    [("小测试不是假装整条链跑过", "view 接收失败只展示旧布局和重试动作。它能快速覆盖状态分支，但不证明服务实际会返回这个状态。"),
     ("契约保护跨层语义", "api 必须区分 retryable 与 invalid。单独断言结构能抓到字段名改动，即使 UI 的旧测试替身仍然通过。"),
     ("窄集成只盯实际连接", "通过把 api 的真实输出交给 view 拼起这一段。仍未涉及浏览器渲染、网络抖动或持久化，真实系统应明确未覆盖范围。")],
    '''
    def view(response, old_revision):
        if response["kind"] == "ready":
            return response["revision"], "none"
        action = "retry" if response["retryable"] else "edit"
        return old_revision, action

    def api(input_width, generate):
        if input_width <= 0:
            return {"kind": "failed", "retryable": False}
        try:
            return {"kind": "ready", "revision": generate()}
        except TimeoutError:
            return {"kind": "failed", "retryable": True}

    def slow():
        raise TimeoutError()

    # Component-level state contract
    assert view({"kind": "failed", "retryable": True}, 2) == (2, "retry")
    # Interface shape contract
    assert api(3, slow) == {"kind": "failed", "retryable": True}
    assert api(0, lambda: 1 / 0) == {"kind": "failed", "retryable": False}
    # Integration of these two boundaries
    assert view(api(3, slow), 2) == (2, "retry")
    assert view(api(3, lambda: 3), 2) == (3, "none")
    ''',
    [("接口错误分类改坏", "超时返回 retryable=False。", "契约测试指出错误，集成也不该再显示重试。"), ("视图映射改坏", "失败路径把旧版清空。", "不需要启动服务，组件断言直接失败。")],
    ["小测试分别只验证一个责任。", "假模型超时能跑到重试 UI。", "成功控制组更新版本，证明不是一律保留旧图。"],
    "失败层知道在哪里，修复就不必靠猜。")

add("structured-output", "让模型输出可验证的布局草案", 22,
    "分开文本解析、结构校验、领域校验与修复。",
    "模型给出像 JSON 的结果，但有多余字段、断掉的输出或越界家具。应用要说明是哪一层失败。",
    ["保留可解析的结构。", "仅接纳定义好的字段。", "领域规则最后判断能否落图。"],
    "用同一房间送入坏 JSON、错字段名与非法坐标。",
    ("模型遵守 JSON Schema 就可以直接发布吗？", ["可以", "还需业务校验和发布审批"], 1, "坐标和审阅属于业务契约。"),
    ("结构化输出", "让结果满足预先规定的字段、类型和分支。"),
    "怎样把内容不对与格式不对分别复现？",
    ["抓取完成的候选。", "解析成对象。", "验证字段与业务边界。", "按类别决定修复或放弃。"],
    [("提示词是合作，不是校验", "即便模型受结构约束，调用也可能被截断或返回拒绝。适配器只在得到完整候选后向下交付。"),
     ("字段齐全不能证明布局正确", "left 和 width 均为整数却依旧可能超出房间。示例将 parse、invalid-shape 和 out-of-bounds 分开。"),
     ("修复有限次并保留边界", "只把字段级失败反馈给模型。修复不能放宽边界；再次返回坏结果时终止，不能替换已经展示的布局。")],
    '''
    import json

    def extract(text, room_width):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return "parse-error", None
        if not isinstance(value, dict) or set(value) != {"left", "width"}:
            return "invalid-shape", None
        left, width = value["left"], value["width"]
        if type(left) is not int or type(width) is not int:
            return "invalid-shape", None
        if left < 0 or width <= 0 or left + width > room_width:
            return "out-of-bounds", None
        return "candidate", (left, width)

    assert extract('{"left":', 4) == ("parse-error", None)
    assert extract('{"left":true,"width":1}', 4) == ("invalid-shape", None)
    assert extract('{"left":3,"width":2}', 4) == ("out-of-bounds", None)
    assert extract('{"left":3,"width":1}', 4) == ("candidate", (3, 1))
    ''',
    [("生成被截断", "候选只写完一半。", "返回解析错误，不进入写工具。"), ("合法结构但坐标超线", "left=3、width=2 而房间宽 4。", "判定领域错误，不把失败归给解析器。")],
    ["解析与规则有不同错误码。", "布尔值不会误当整数坐标。", "几何约束通过也只代表得到候选，并未保存。"],
    "模型产出只是候选，能否发布由应用的验证与决策共同决定。")

add("context-isolation", "给每个任务一份独立而可重现的上下文", 22,
    "防止并行任务把不同房间的规则拼到同一次模型调用。",
    "旧任务的模型请求被延迟，用户已经切到另一个房间。若生成时去读界面当前选项，可能组合出错误的输入。",
    ["生成时冻结输入快照。", "将房间身份放入缓存键。", "只选择本房间的资料。"],
    "先冻结 A 的上下文，再编辑 A、切到 B，检查旧执行身份与新版输入。",
    ("上下文缓存只按用户编号区分够吗？", ["够", "不够，应绑定房间与规则版本等输入"], 1, "同一用户也可并行生成不同房间。"),
    ("快照", "将容易随页面操作变化的生成输入固定在本次操作中。"),
    "同时生成两个房间时，如何防止模型读到串线的规则？",
    ["从当前选择构建不可变请求。", "读对应版本规则与允许的资料。", "用快照计算稳定标识。", "把标识用于调试、恢复和缓存。"],
    [("延迟读取是隐藏变量", "工作者不能在看来应该读取输入时去访问可变的当前房间。冻结规则数值、约束版本与文档 ID，可以让重试的语义不变。"),
     ("限制资料进入模型上下文", "在拼接前过滤所属房间，按确定顺序排序并限制数量。示例仅保留标识；检索后还需要重新校验权限与事实。"),
     ("缓存身份与执行身份不同", "执行 ID 用来追踪一次调用，缓存键代表什么输入可以共享结果。生产应纳入模型、提示版本和访问作用域等影响结果的维度。")],
    '''
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Context:
        room: str
        rules_rev: int
        width: int
        docs: tuple[str, ...]

    def freeze(selected, notes):
        permitted = tuple(sorted({
            n["id"] for n in notes if n["room"] == selected["room"]
        })[:2])
        return Context(selected["room"], selected["rules_rev"], selected["width"], permitted)

    a = {"room": "A", "rules_rev": 1, "width": 4}
    notes = [{"room": "A", "id": "furniture"}, {"room": "B", "id": "desk"}]
    snapshot = freeze(a, notes)
    a["width"] = 6
    assert snapshot.width == 4
    assert snapshot.docs == ("furniture",)
    assert freeze(a, notes) != snapshot
    assert freeze({**a, "room": "B"}, notes).docs == ("desk",)
    ''',
    [("旧请求晚执行", "冻结后修改宽度。", "旧请求输入仍是原尺寸。"), ("同用户跨房间并行", "A 和 B 的资料均存在。", "A 只引用 A 的资料。")],
    ["输入切换不修改已排队上下文。", "快照标识区分不同规则和房间。", "跨房间资料在拼装前被排除。"],
    "把上下文当作正式输入固定下来，而不是运行中随手读取的页面状态。")

add("stream-protocol", "区分流字节、消息帧与业务事件", 24,
    "看清为什么数据一次读到了也不等于事件完整。",
    "RoomLab 的流在本地总是一次读完整行，稍慢的网络上却会在两个字符之间切分消息。",
    ["用增量解码得到字符。", "按协议边界拼完整帧。", "只交付已经解析并校验的业务事件。"],
    "把同一个示例流切成 1 字节一段，比较与一次读完的结果。",
    ("一次网络 read 等于一次业务消息吗？", ["不等于", "等于"], 0, "传输切片与应用分帧是两个层次。"),
    ("分帧", "从连续字节中识别出每条完整消息的边界。"),
    "一个汉字分在两个传输块里时，为什么不能把每块直接转 JSON？",
    ["收到字节片段。", "UTF-8 增量解码。", "按换行找完整记录。", "解析后把事件交给状态更新。"],
    [("这里只讲 NDJSON", "每条 JSON 一行并以换行结束；这不是 SSE 解析器。SSE 按空行结束事件，还支持多行 data 与重连标识。"),
     ("字节和字符是不同层", "增量解码器保存未完成的多字节字符；缓冲区保存未完成的消息。超长帧需要限制，免得坏流占满内存。"),
     ("断开时不要推测", "尾部无分隔符就不是完整帧。按上一课的状态快照恢复，而不是拿残句猜完成。")],
    r'''
    import codecs, json

    def frames(chunks, limit=120):
        decoder = codecs.getincrementaldecoder("utf-8")()
        pending = ""
        for chunk in chunks:
            pending += decoder.decode(chunk)
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                if len(line) > limit:
                    raise ValueError("frame too long")
                if line.strip():
                    yield json.loads(line)
            if len(pending) > limit:
                raise ValueError("frame too long")
        pending += decoder.decode(b"", final=True)
        if pending:
            raise ValueError("stream ended mid-frame")

    data = '{"seq":1,"phase":"准备"}\n{"seq":2,"phase":"完成"}\n'.encode()
    assert [x["seq"] for x in frames([data])] == [1, 2]
    assert list(frames([data[i:i+1] for i in range(len(data))])) == list(frames([data]))
    try:
        list(frames([b'{"seq":3}']))
        raise AssertionError("expected truncation")
    except ValueError as exc:
        assert "mid-frame" in str(exc)
    ''',
    [("UTF-8 拆开", "把字节逐个喂入。", "获得跟完整输入相同的两个事件。"), ("流无分隔符断开", "移除最后的换行。", "报告半帧，不能制造完成事件。")],
    ["任意切片不改变解码结果。", "连续两帧不会合并成一条记录。", "截断需走恢复，不将半帧当终态。"],
    "先把传输数据恢复成合法消息，再用业务状态规则消费它。")

add("durable-worker", "工作进程重启后如何接回任务", 25,
    "用领取、租约和完成条件模拟安全接手。",
    "一个进程拿到布局任务后停止响应。另一个进程接手时，旧进程可能稍后重新活过来，带着旧结果回来。",
    ["每次领取都有唯一代号。", "过期任务能被新工作者接手。", "提交结果时仍核对领取身份。"],
    "让 A 过期后由 B 接手，再让 A 的完成事件先回来。",
    ("只靠租约超时能阻止旧工作者写结果吗？", ["不能", "能"], 0, "还要让持久化写入核对领取身份。"),
    ("租约", "工作者在一定期限内拥有处理权，过期后允许接手。"),
    "为什么新工作者接手后，还要拦旧工作者的完成？",
    ["领取获得递增代次。", "读取必要的中间状态。", "过期后由下一代接手。", "提交时比较自己的代次和当前代次。"],
    [("接手不等于安全终止旧进程", "进程停顿后可能恢复。不能仅靠内存中的定时器或网络连接识别当前唯一工作者。"),
     ("代次用于持久化屏障", "这个单进程模型每次领取递增代次。真实系统必须在数据库原子领取与写入时比较，不允许旧代夺回任务。"),
     ("外部副作用也要防重复", "旧进程已经向外部工具发请求的情况，仅阻止其向任务表回写并不够。工具写操作仍需要幂等键或等价防重策略。")],
    '''
    class QueueRow:
        def __init__(self):
            self.epoch, self.until, self.result = 0, 0, None

        def claim(self, now, ttl):
            if self.result is not None or now < self.until:
                return None
            self.epoch += 1
            self.until = now + ttl
            return self.epoch

        def finish(self, epoch, now, result):
            if epoch != self.epoch or now >= self.until or self.result is not None:
                return False
            self.result = result
            return True

    row = QueueRow()
    first = row.claim(now=0, ttl=5)
    assert row.claim(now=4, ttl=5) is None
    second = row.claim(now=5, ttl=5)
    assert second != first
    assert not row.finish(first, now=6, result="old")
    assert row.finish(second, now=6, result="new")
    assert row.result == "new" and row.claim(now=11, ttl=5) is None
    ''',
    [("处理超时", "A 未在期限内完成，B 在到期时领取。", "B 能拿到新代次。"), ("旧进程回归", "B 领取后 A 尝试提交。", "拒绝 A，最终只保留 B 的结果。")],
    ["租期未到不会重复领取。", "旧代即使先返回也不能写。", "有终态后不再领取。"],
    "持久任务恢复必须保护交接窗口，而不只是能把任务重新拿起来。")

add("outbox", "写入已成功，完成事件为何可能没发出", 25,
    "用同一事务存版本与待送事件，并练习重发与去重。",
    "后台保存成功后进程立刻退出，客户端仍在等推送；另一种情况是推送已送达但服务还没来得及记已送。",
    ["在同一事务写布局和待送记录。", "发送器独立读取未发送事件。", "用稳定事件编号在消费端去重。"],
    "写两次试验：一次在保存后停发；一次发送后停在确认前。",
    ("Outbox 能保证消费者永远不会收到重复吗？", ["不能，仍要幂等消费", "能，严格一次"], 0, "发送成功与记录已发送之间仍存在失败窗口。"),
    ("Outbox", "存储业务变更时一并写待发送记录，之后另由发送者送出。"),
    "如何同时避免保存后丢通知和重发时重复更新？",
    ["开始事务。", "修改布局并写 outbox。", "发送后记录送达。" , "同编号消息在消费端只影响一次结果。"],
    [("同一事务消除半个结果", "事件与业务行要么同在、要么同无。示例用 SQLite 的失败注入验证回滚，不能把事务跨越到外部消息系统。"),
     ("重发正常，丢失才不可接受", "写入成功而发送器没运行时，待送记录仍在。发送成功后未记送达，重启后可能再次发，所以不能声称严格一次传输。"),
     ("去重记录需要稳定耐久", "本示例用集合表达消费不变量；跨进程真实系统要在数据库中将去重和业务副作用原子提交。")],
    '''
    import sqlite3
    db = sqlite3.connect(":memory:")
    db.executescript("CREATE TABLE layout(rev INT); "
                     "INSERT INTO layout VALUES(2); "
                     "CREATE TABLE pending(event TEXT PRIMARY KEY, revision INT);")

    def save(rev, fail=False):
        with db:
            db.execute("UPDATE layout SET rev = ?", (rev,))
            if fail:
                raise RuntimeError("stop before outbox")
            db.execute("INSERT INTO pending VALUES(?, ?)", (f"done-{rev}", rev))

    try:
        save(3, fail=True)
    except RuntimeError:
        pass
    assert db.execute("SELECT rev FROM layout").fetchone() == (2,)
    assert db.execute("SELECT COUNT(*) FROM pending").fetchone() == (0,)
    save(3)
    event = db.execute("SELECT event FROM pending").fetchone()[0]
    consumed = set()
    for delivery in (event, event):
        consumed.add(delivery)
    assert consumed == {"done-3"}
    ''',
    [("同一事务中断", "布局写后、待送记录写前抛错。", "保留原版本，不出现孤立更新。"), ("确认前中断", "同一事件被再次投递。", "只能生效一次。")],
    ["失败注入验证的是事务回滚，不是现场补数据。", "重新发送使用稳定同一事件编号。", "传输次数可能为二，业务生效次数为一。"],
    "让事件记录和业务结果一起落地；允许重发，然后在边界消除重复作用。")

add("trace-metrics", "把一次失败变成可汇总的运行指标", 21,
    "用低基数维度统计失败，明白日志与指标各该记录什么。",
    "偶发生成失败每天几十条。团队既想知道失败都发生在哪一层，又想点开一次具体运行复盘。",
    ["先定义允许的阶段和结果。", "每次尝试保留关联标识。", "汇总时只按阶段和结果聚合。"],
    "把同一条终态重复上报，再将两次不同 attempt 送入指标。",
    ("把运行编号作为指标标签有什么风险？", ["时序数跟着运行数增长", "可以让看板计算更快"], 0, "高基数标签会使监控成本上升。"),
    ("基数", "同一标签能出现多少不同取值。"),
    "怎样让看板稳定，具体错误又可追溯？",
    ["写结构化阶段事件。", "按尝试身份消除重复。", "只用有限标签创建指标。", "具体运行用追踪记录查询。"],
    [("日志与指标的查询目标不同", "排查一次运行需要关联编号；找全体趋势需要阶段、结果和固定时间范围。把两种目标塞一个维度，既难查又昂贵。"),
     ("先确定统计单位", "示例统计一次尝试的一条完成事件，不以每次重传为新执行。同一任务重跑第二次会增加尝试计数。若产品关注用户最终体验，可以另做按运行计数。"),
     ("未识别分类不任其增长", "未知阶段或结果枚举拒收；维护监控时应记录单独的事件格式错误指标。避免动态错误文本变成标签。")],
    '''
    from collections import Counter
    ALLOWED_PHASES = {"generate", "validate", "publish"}
    ALLOWED_OUTCOMES = {"ok", "timeout", "invalid"}

    def summarize(events):
        totals, seen = Counter(), set()
        for run, attempt, phase, outcome in events:
            if phase not in ALLOWED_PHASES or outcome not in ALLOWED_OUTCOMES:
                continue
            identity = (run, attempt, phase)
            if identity in seen:
                continue
            seen.add(identity)
            totals[(phase, outcome)] += 1
        return totals

    slow = ("run-1", 1, "generate", "timeout")
    done = ("run-1", 2, "generate", "ok")
    wrong = ("run-2", 1, "user-chosen-label", "ok")
    totals = summarize([slow, slow, done, wrong])
    assert totals[("generate", "timeout")] == 1
    assert totals[("generate", "ok")] == 1
    assert len(totals) == 2
    ''',
    [("重复投递", "同一次尝试上报两遍。", "超时计数仍是一。"), ("动态错误标签", "阶段字段给自由文本。", "不创建新指标序列。")],
    ["每个指标键只含有限枚举。", "同次尝试重复上报不增加计数。", "重跑成功与初次超时都可识别。"],
    "用指标找整体问题，再用关联信息查个案，不让一个维度承担两种目标。")

add("latency-budget", "区分等待、模型慢和渲染慢", 21,
    "根据耗时边界定位瓶颈，避免把并行时间重复算进总耗时。",
    "同一次生成的总时间看起来变慢。模型和读取规则并行，直接相加会高估总耗时。",
    ["拆出排队、首个反馈与最终可用。", "把并行阶段按同一时间轴计算。", "根据瓶颈与门槛决定优先级。"],
    "把规则从串行改为并行，分别计算首反馈和最终耗时。",
    ("两段并行工作各 1 秒，等待两者完成至少多久？", ["约 1 秒", "必然 2 秒"], 0, "并行的公共区间不重复计入。"),
    ("关键路径", "必须依次等待的最长依赖链，决定基础完成时间。"),
    "为什么各阶段耗时相加会比用户实际等待更长？",
    ["记下进入队列及各支路边界。", "找并行分支汇合点。", "计算首反馈和最终可用的时间。", "分别对照阈值定位退化。"],
    [("不要拿首反馈代替完成", "即便页面 30 毫秒先出现正在生成，用户仍可能几秒后才看到图。两个指标分别反映感知确认和真正完成。"),
     ("并行支路取最迟结束", "示例两个并行分支都在排队结束后开始，因此汇合时间取较慢的一个，再加后置校验或渲染。依赖有分组时需计算真实关键路径。"),
     ("样本与分位数", "性能对比应用同类房间与工作负载测 P50/P95，并按房间复杂度分桶。不能拿一次手工测量声称整体提速。")],
    '''
    def timeline(queue, model, rules, render):
        first_feedback = queue
        joined = queue + max(model, rules)
        finish = joined + render
        return {
            "feedback": first_feedback,
            "ready": finish,
            "critical": "model" if model >= rules else "rules",
        }

    normal = timeline(queue=40, model=260, rules=80, render=60)
    assert normal == {"feedback": 40, "ready": 360, "critical": "model"}
    slow_rules = timeline(queue=40, model=260, rules=500, render=60)
    assert slow_rules["ready"] == 600
    assert slow_rules["critical"] == "rules"

    queue_issue = timeline(queue=300, model=260, rules=80, render=60)
    assert queue_issue["feedback"] == 300
    assert queue_issue["ready"] == 620
    ''',
    [("并行误加", "把模型耗时和规则耗时相加。", "得到 440，而正确汇合后的完成耗时为 360。"), ("命中错误瓶颈", "模型不变，规则突然变为 500。", "关键等待是规则，不该先优化模型。")],
    ["并行支路只计算最晚结束点。", "首反馈指标能识别排队变慢。", "规则或模型变慢可以切换关键分支。"],
    "先量清用户在等什么，再决定哪一段优化最有用。")

add("layout-eval", "用固定样本验证模型改变后有没有退化", 25,
    "把几何硬约束和偏好评分分开，保留失败个案。",
    "换模型后，更多方案看起来漂亮，却有小房间交付越界。单一平均分可能隐藏这类退化。",
    ["冻结同一组房间样本。", "先判硬性规则。", "再比较通过项的偏好分。", "逐样本列出新失败。"],
    "给不同模型输出相同四个样本，调高一项软偏好但引入一个越界。",
    ("平均偏好更高，能覆盖新增越界吗？", ["不能", "能"], 0, "硬约束退化不能被软分抵消。"),
    ("回归语料", "每次用相同输入和判分规则重复运行的一组样本。"),
    "怎样核实模型表现真的变好了，而非只是更适合挑出来的样本？",
    ["固定样本和判分规则。", "区分硬失败与偏好分。", "比较同 ID 的两次结果。", "保存新增失败的复现输入。"],
    [("规则优先且失败保留", "若输出侵占房间边界，再高的偏好分也无意义。示例先保留新增失败列表，再对双方都通过的项目比较得分。"),
     ("不能把筛掉的失败样本算成进步", "仅比较两个模型的通过项平均分可能比较的是不同样本。共同通过的样本适合成对比较；同时报告各模型通过集合。"),
     ("波动与版本", "真实模型可能随机。要保存基线系统参数、评分规则版本，并为高波动样本增加重复次数。本例只展示确定性判分与比较。")],
    '''
    rooms = {"narrow": 3, "wide": 8, "corner": 4}
    baseline = {"narrow": (1, 1, 3), "wide": (2, 2, 4), "corner": (0, 2, 4)}
    changed = {"narrow": (2, 2, 5), "wide": (1, 2, 5), "corner": (0, 2, 4)}

    def score(outputs):
        result = {}
        for name, limit in rooms.items():
            x, size, preference = outputs[name]
            safe = x >= 0 and size > 0 and x + size <= limit
            result[name] = preference if safe else None
        return result

    old, new = score(baseline), score(changed)
    regressions = [key for key in old if old[key] is not None and new[key] is None]
    paired = [key for key in rooms if old[key] is not None and new[key] is not None]
    delta = sum(new[key] - old[key] for key in paired) / len(paired)

    assert regressions == ["narrow"]
    assert paired == ["wide", "corner"]
    assert delta == 0.5
    assert new["narrow"] is None
    ''',
    [("增加越界但偏好更高", "狭长房间改用更宽家具。", "定位到 narrow，不能因共同样本软分增加就整体发布。"), ("比较集合错误", "只算各自通过项的均值。", "识别两个均值没有按同样输入比较；改看配对差。")],
    ["硬失败与偏好均值分开呈现。", "新增越界由样本 ID 定位。", "成功配对不吸收任何失败样本。"],
    "先守住布局可用，再比较主观偏好，出问题就能复现。")

add("multi-room-rollout", "真实项目练习：批量生成与安全回退", 27,
    "按房间隔离进展和失败，从小范围发布到可回退。",
    "RoomLab 要一次替两个房间生成布局。当第二个失败，第一个成功不该被撤销，也不应切换全局就把成功和失败一起覆盖。",
    ["将批次拆成独立房间任务。", "先只发布到允许的试点房间。", "分别更新成功项。", "停止扩大范围并保留已确认版本。"],
    "指定仅 room-A 试点，再模拟两个房间都生成、后一房间失败和回退之后迟到旧结果。",
    ("关闭试点后，已确认布局也必须从用户界面清空吗？", ["不用，可按回退目标停止新写入并保留已确认数据", "必须"], 0, "停止新变更与删除现有数据是不同动作。"),
    ("试点范围", "正式扩大前允许新功能生效的一小组对象。"),
    "批量生成坏一个房间，怎么做到问题可止损、影响范围清楚？",
    ["每个任务携带房间与试点代次。", "验证任务归属和结果。", "更新成功项并留存失败原因。", "关试点后拒绝旧代提交。"],
    [("批次成功不等于每项成功", "UI 需要展示房间粒度的状态。先决定业务是否允许部分成功；本场景允许，因为两个房间布局彼此独立。"),
     ("只控制应用发布，不要倒推任务已取消", "停止试点后旧任务可能仍执行。写前核对试点代次和范围，旧通知不能借此前授权继续更新。"),
     ("有记录的回退更安全", "本例的回退只禁止新写、保留成功数据。若业务要恢复旧版本，应为每个房间另启一次可审阅、可追踪的发布，不覆盖这次证据。")],
    '''
    versions = {"A": 2, "B": 4}
    allowed = {"A", "B"}
    epoch = 1

    def publish(room, task_epoch, valid):
        if task_epoch != epoch or room not in allowed:
            return "blocked"
        if not valid:
            return "invalid"
        versions[room] += 1
        return "released"

    assert publish("A", 1, True) == "released"
    assert publish("B", 1, False) == "invalid"
    assert versions == {"A": 3, "B": 4}

    epoch += 1
    allowed.clear()
    assert publish("A", 1, True) == "blocked"
    assert publish("B", 2, True) == "blocked"
    assert versions == {"A": 3, "B": 4}
    ''',
    [("两个房间一成一败", "让 A 通过、B 生成坏方案。", "只更新 A 的已确认版本，B 留在原版本。"), ("关闭试点后迟到", "撤销范围，再交来旧代成功结果。", "拒绝提交，不修改已确认数据。"), ("重发同一项", "重复发相同业务操作。", "在真正发布器中用上一阶段的持久幂等键去重；这段控制点不承担去重。")],
    ["试点覆盖范围和任务代次必须同时匹配。", "失败房间不影响成功房间。", "停止新写仍保留已确认版本。"],
    "从项目验收角度同时证明两件事：允许的变更确实生效，不该发生的变更能够被挡住。")
