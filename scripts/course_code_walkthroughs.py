"""Clean-room public examples for the two project walkthroughs."""


AI_DEPTH = {
    "request": (
        "点一次「生成布局」，为什么页面先出现排队提示，而不是立刻画出新布局？",
        ["页面把此次点击标成一个独立操作，同时保留当前布局。", "服务确认收单，返回可查询的任务编号；此时没有新布局可显示。", "页面接收结果时核对任务编号与当前操作。", "结果通过检查后，二维和三维从同一个新版本更新。"],
        [
            ("先看 UI 里两样东西：任务和布局", "任务表示这次生成做到哪一步，布局表示用户此刻正在看的图。示例用 pending 记录任务编号，revision 记录布局版本。只要服务还没产生可用结果，即使任务已排队，也不该把版本 2 清成空白。"),
            ("收单与完成更新不同字段", "accept 先判断响应是不是当前点击。如果响应属于较早的点击，不更新 pending。应用在发请求前先递增 click，把点击编号保存到请求的回调中。这个编号用于本页防止旧回调覆盖，不是后台任务编号。"),
            ("按身份和结果类型决定是否发布", "finish 只接收当前任务的结果；失败时只更新任务状态，成功且版本不倒退时同时更新布局版本。示例的 revision 只表示同一房间里的版本，真实应用还应校验当前房间，切图前也应校验结果结构。页面在实际提交前可用订阅后的快照覆盖可能过早到达的通知。"),
        ],
        "javascript",
        """const assert = require('node:assert/strict');
const initial = { click: 0, pending: null, state: 'idle', revision: 2 };
const send = (s) => ({ ...s, click: s.click + 1, pending: null, state: 'sending' });

function accept(s, click, id) {
  if (s.click !== click || s.state !== 'sending') return s;
  return { ...s, pending: id, state: 'queued' };
}

function finish(s, result) {
  if (s.state !== 'queued' || result.id !== s.pending) return s;
  if (!result.ok || !Number.isInteger(result.revision) || result.revision <= s.revision) {
    return { ...s, state: 'failed', pending: null };
  }
  return { ...s, pending: null, state: 'ready', revision: result.revision };
}

const a = send(initial);
const b = send(a);
assert.equal(accept(b, a.click, 'old').pending, null);
const queued = accept(b, b.click, 'sample-2');
assert.equal(queued.revision, 2);
assert.equal(finish(queued, { id: 'old', ok: true, revision: 9 }), queued);
assert.equal(finish(queued, { id: 'sample-2', ok: false }).revision, 2);
const ready = finish(queued, { id: 'sample-2', ok: true, revision: 3 });
assert.equal(ready.revision, 3);""",
        [("旧回执迟到", "先发 A 再发 B，最后收到 A 的回执。", "页面继续等待或展示 B，A 不能改当前任务。"), ("新任务失败", "后台回失败，或者回传无法使用的版本。", "任务进入失败，但两张视图仍显示版本 2。"), ("完成消息先于订阅", "模拟切换网络，接收回执之后才接上消息。", "订阅后以同任务快照补齐进度，不假设当前仍在排队。")],
        ["收到回执以后，版本仍是 2。", "旧任务报告更大的版本，也不能更新当前运行。", "失败不抹掉已确认布局，成功才切到版本 3。"],
        "先认清是哪个请求、哪个任务，再问有无足够信息替换布局。"
    ),
    "service": (
        "把模型从成功换成超时，能不能只改一行测试输入就验证整个后端分支？",
        ["接口先校验房间尺寸，把请求转成明确输入。", "应用函数向一个可替换的生成器请求草案。", "规则函数检查草案坐标，决定能否接纳。", "只有通过检查的结果才获得新版本。"],
        [
            ("三层职责对应三种错误", "输入不合法应在模型调用前结束；模型超时说明生成尚无结果，不表示房间本身不合法；草案越界说明模型返回了结果但结果不可采纳。把三个类别都叫「生成失败」会让 UI 和测试没法判断如何恢复。"),
            ("用函数参数接住变化", "generate 可以是模型适配器，也可以是返回固定结果的测试函数。规则层不依赖它内部使用哪种技术，适配层应把上游异常翻译成应用已知的错误。这个例子只捕获 TimeoutError；未预期的程序错误不伪装成超时。"),
            ("定一个很小的可验证契约", "示例把房间当作一条长度线，只检查一件家具的左边与右边是否在界内，以便单独验证单位和边界。多件家具的重叠、碰撞与旋转应有单独的规则和用例，不宜在这里假定已验证。"),
        ],
        "python",
        """def propose_revision(room_width, old, generate):
    if type(room_width) is not int or room_width <= 0:
        return ("invalid-input", old)
    try:
        draft = generate(room_width)
    except TimeoutError:
        return ("retryable-timeout", old)

    if not isinstance(draft, dict):
        return ("invalid-draft", old)
    left, width = draft.get("left"), draft.get("width")
    valid = (
        type(left) is int and type(width) is int
        and left >= 0 and width > 0 and left + width <= room_width
    )
    if not valid:
        return ("invalid-draft", old)
    return ("accepted", {
        "revision": old["revision"] + 1,
        "shape": {"left": left, "width": width},
    })

base = {"revision": 2, "shape": {"left": 0, "width": 1}}

def timeout(_):
    raise TimeoutError()

assert propose_revision(5, base, timeout) == ("retryable-timeout", base)
assert propose_revision(5, base, lambda _: {"left": 4, "width": 2})[1] is base
assert propose_revision(5, base, lambda _: {"left": 4, "width": 1})[1]["revision"] == 3
assert propose_revision(0, base, lambda _: 1 / 0)[0] == "invalid-input" """,
        [("非法输入", "把房间宽度设为 0，生成器故意一调用就报错。", "不会调用生成器，返回可识别的输入错误。"), ("超时", "注入主动抛出 TimeoutError 的生成器。", "能区分超时和草案非法，两者都不发布新版本。"), ("越一格", "宽 5，左坐标 4，分别用宽 1 与宽 2。", "恰好贴边通过，越过一格失败。")],
        ["同一份旧布局在失败路径不被修改。", "非法请求不调用模型适配器。", "只有合法草案出现在下一版本，且边界值等于房间宽度可接受。"],
        "应用定义错误和发布规则，适配器只负责把模型输入输出接进来。"
    ),
    "stream": (
        "生成进度先到 1，再到 3，重连时又收到 2。应该接受哪条？",
        ["服务为任务里的状态事件标上局部序号。", "客户端先排除其他任务、重复或落后的序号。", "遇到缺口时暂停消化新事件，启动一次快照读取。", "只接收当前任务且不倒退的快照；若快照未覆盖缺口，继续补查。"],
        [
            ("任务编号与版本是两道阀门", "A 的第 8 条和 B 的第 2 条不属于同一把尺子。代码先比较 run 再比较 seq。否则一个以前的任务只要序号足够大，就能覆盖最新任务。"),
            ("补查目标记录已看见的最高事件", "本例选择不缓存所有事件，而只保存 want。看到第 3 条就记住要补到至少 3；期间如果见到第 5 条，恢复要求推到至少 5。由服务端快照重建状态，而不是把第 3 条的状态字段猜成完整状态。"),
            ("快照也可能迟到", "收快照时不仅校验任务身份，还比较快照序号。快照给的是全量，所以 seq 足够且数据契约满足时可直接替换；不够时维持 syncing。显示层在应用事件前也要检查负载结构。应用层要单飞、退避和设上限，不在每条重复通知上新开请求。"),
        ],
        "javascript",
        """const assert = require('node:assert/strict');
const start = { run: 'room-run-A', seq: 1, phase: 'generating', want: 1 };
const syncing = (s) => s.want > s.seq;

function receive(s, event) {
  if (event.run !== s.run || event.seq <= s.seq) return s;
  if (syncing(s) || event.seq !== s.seq + 1) {
    return { ...s, want: Math.max(s.want, event.seq) };
  }
  return { ...s, seq: event.seq, want: event.seq, phase: event.phase };
}

function snapshot(s, state) {
  if (state.run !== s.run || state.seq < s.seq) return s;
  return { ...s, ...state, want: Math.max(state.seq, s.want) };
}

const gap = receive(start, { run: start.run, seq: 3, phase: 'ready' });
assert.equal(gap.phase, 'generating');
assert.equal(syncing(gap), true);
const partial = snapshot(gap, { run: start.run, seq: 2, phase: 'validating' });
assert.equal(syncing(partial), true);
const fixed = snapshot(partial, { run: start.run, seq: 3, phase: 'ready' });
assert.equal(syncing(fixed), false);
assert.equal(receive(fixed, { run: start.run, seq: 3, phase: 'ready' }), fixed);
assert.equal(snapshot(fixed, { run: 'other', seq: 99, phase: 'failed' }), fixed);""",
        [("缺号", "当前为 1，直接收到 3，并暂时只读到序号 2 的快照。", "先更新到快照 2，但仍需要再获取一次，不能宣布补齐。"), ("重复终态", "快照已经在 3，再收到两条 3。", "状态不变；原先的发布动作不触发第二次。"), ("连接切换", "切到新任务后，旧任务的快照或事件才到。", "都不能覆盖新任务。")],
        ["序号 1 跳到 3 时，业务结果不直接变为 ready。", "快照 2 仍未达到追赶目标，快照 3 能恢复。", "回放重复终态或旧任务快照，结果保持不变。"],
        "推送改善反应速度；序号和快照决定断线后能否回到正确结果。"
    ),
    "agent": (
        "确认保存后网络断了。下一位执行者如何知道该补写，还是只该找回已写入的结果？",
        ["生成草案并保存草案引用。", "验证草案和用户确认，固定本次操作身份。", "保存前先按操作身份寻找已有结果。", "写入结果未知时停止盲目追加；恢复时同键查询或幂等写。"],
        [
            ("草案与提交记录不能混成一份", "草案是模型建议，提交是可被别的用户操作看到的变更。checkpoint 只用于保存执行进度，不等同于所有副作用都已发生。示例把用户确认与草案校验作为前置条件，不根据模型一句「可以提交」判断。"),
            ("同一业务动作只发一个身份", "key 由任务与草案组成，是示例中稳定不变的身份。真实服务应把键绑定资源、作用域以及请求语义；同键却换内容通常应拒绝，而非悄悄拿旧结果成功返回。应用层的先查只能避免已知重复，数据库仍需唯一约束或等价原子写入，避免两个执行者同时通过检查。"),
            ("用想知道的事实分支", "正常写入返回新版本；响应丢失时运行停在 unknown。示例把故障放在写入之后，以便验证重跑时没有第二条记录。线上只有读取可靠源或得到已存在的幂等响应，才可以结束未知状态；读取不到而系统可能仍在执行时，应保留待确认。"),
        ],
        "python",
        """class DemoStore:
    def __init__(self):
        self.rows = {}

    def commit_once(self, key, shape, lose_reply=False):
        if key not in self.rows:
            self.rows[key] = (len(self.rows) + 3, shape)
        elif self.rows[key][1] != shape:
            raise ValueError("same operation, different shape")
        if lose_reply:
            raise TimeoutError("reply lost after write")
        return self.rows[key]

def commit(store, run, draft_id, shape, *, checked, confirmed, lose_reply=False):
    if not checked or not confirmed:
        return ("blocked", None)
    key = (run, draft_id)
    try:
        result = store.commit_once(key, shape, lose_reply)
    except TimeoutError:
        return ("unknown", None)
    return ("done", result[0])

store = DemoStore()
shape = (1, 2)
assert commit(store, "R", "D", shape, checked=True, confirmed=False) == ("blocked", None)
assert commit(store, "R", "D", shape, checked=True, confirmed=True, lose_reply=True)[0] == "unknown"
assert commit(store, "R", "D", shape, checked=True, confirmed=True) == ("done", 3)
assert len(store.rows) == 1""",
        [("写后响应丢失", "先保存再抛出超时，随后同键恢复一次。", "最初状态为未知，恢复后找回版本 3，保存记录仍只有一条。"), ("恢复请求改了草案", "保留同一个执行编号和草案 ID，但改坐标。", "判定身份冲突；不会覆盖已记录结果。"), ("没有用户确认", "草案校验通过，但确认尚未发生。", "写操作完全不发生。")],
        ["确认前记录数是 0。", "超时确实发生在保存后，而非保存前。", "恢复拿到同一版本，持久化次数仍是 1。"],
        "恢复用来找回流程和结果；副作用是否能再做，要靠业务身份与存储约束回答。"
    ),
    "tool": (
        "Agent 看到了「保存草案」工具，也传了形状正确的参数，为什么还不一定能执行？",
        ["可用工具约定名称、入参类型和结果。", "模型提出工具请求，而应用从自己的可信状态读取授权。", "应用校验访问范围、参数、草案版本和确认。", "工具返回结构化数据；旁白不作为新的用户授权。"],
        [
            ("这是应用边界，不是协议实现", "工具协议解决发现和调用，调用前的资源身份与用户许可是应用职责。示例调用的是普通函数，用这一层模拟协议客户端发出调用前应该做的判断，不涉及外部服务配置。"),
            ("每次审批要绑定到要写的内容", "用 room、draft、revision 绑定确认。课例用元组表示三者一致；真实应用还要绑定发起者、允许的动作及确认有效期。处理重复写入依旧依赖上一节的幂等持久化，不由确认元组替代。"),
            ("错误分得开，评测才能写得准", "未知工具、参数不合法、范围错误、缺少确认产生不同结果。模型输出可能提出新的范围，也可能把工具文本当指令。dispatch 只允许预先定义的行为，不把模型文本中的判断当作可执行规则。"),
        ],
        "python",
        """def dispatch(name, args, *, current_room, accepted, calls):
    if name not in {"read_rules", "publish_draft"}:
        return "unknown-tool"
    if not isinstance(args, dict):
        return "invalid-arguments"
    if not isinstance(args.get("room"), str):
        return "invalid-arguments"
    if args["room"] != current_room:
        return "out-of-scope"
    if name == "read_rules":
        calls.append(("read", current_room))
        return {"min_width": 1}

    draft, revision = args.get("draft"), args.get("revision")
    if not isinstance(draft, str) or type(revision) is not int:
        return "invalid-arguments"
    if accepted != (current_room, draft, revision):
        return "needs-confirmation"
    calls.append(("publish", current_room, draft, revision))
    return "published"

calls = []
args = {"room": "room-A", "draft": "sample", "revision": 4}
assert dispatch("publish_draft", args, current_room="room-A", accepted=None, calls=calls) == "needs-confirmation"
assert not calls
assert dispatch("publish_draft", args, current_room="room-A", accepted=("room-A", "sample", 3), calls=calls) == "needs-confirmation"
assert dispatch("publish_draft", args, current_room="room-A", accepted=("room-A", "sample", 4), calls=calls) == "published"
assert len(calls) == 1""",
        [("模型自行声称已确认", "参数齐全，但应用记录中没有确认。", "返回 needs-confirmation，写工具调用次数为 0。"), ("确认后草案变化", "用户批准版本 3，模型提交版本 4。", "继续要求确认，不放行新版草案。"), ("读取别的房间", "让读取工具携带和当前房间不相等的编号。", "返回范围错误，即使是只读工具也不能越过资源权限。")],
        ["工具未知时不发送请求。", "版本不匹配时没有副作用。", "严格匹配已确认动作后，只记录一次写调用。"],
        "工具在清单上不等于行动被允许；权限、参数与确认要在调用处落实。"
    ),
    "views": (
        "二维图点中椅子，再旋转三维相机，哪一份数据应该变、哪一份绝不能变？",
        ["领域状态用同一单位储存家具与稳定编号。", "二维图用像素比例投影，三维视图用空间轴投影。", "两张视图把选中状态映射到相同家具编号。", "相机、缩放等各自保存在视图状态，重画不修改领域布局。"],
        [
            ("一份领域布局，两份派生结果", "领域里的 x、y 统一以米表示。二维 px = x × scale；这个示例规定三维把地面 y 放到 z 轴，把高度放到 y 轴。别隐去具体假设，混用比例或轴向会让联动在同样数据下出现偏移。"),
            ("对象身份不要依赖列表位置", "两张视图的排序可能不同，甚至有对象被裁剪。选择使用 chair-A 这种稳定标识；投影只根据 ID 涂高亮。全量布局发布后，若所选家具已不存在，交给选择层清掉有效选中，不要让列表中下一项自动继承。"),
            ("两个层次的版本", "布局版本来自领域，镜头角度来自当前视图。旋转相机后重建三维投影输入，检查二维输出与领域布局不受影响。若真正的渲染器异步初始化，应为投影作业记住布局版本；画面提交时丢掉旧作业结果。"),
        ],
        "javascript",
        """const assert = require('node:assert/strict');
const layout = Object.freeze({
  revision: 3,
  items: Object.freeze([Object.freeze({ id: 'chair-A', x: 1.2, y: 2.1 })])
});

function plan(model, scale, selected) {
  return model.items.map(item => ({
    id: item.id,
    point: [Math.round(item.x * scale), Math.round(item.y * scale)],
    selected: item.id === selected
  }));
}

function scene(model, camera, selected) {
  return {
    revision: model.revision,
    camera: { ...camera },
    objects: model.items.map(item => ({
      id: item.id, xyz: [item.x, 0, item.y], selected: item.id === selected
    }))
  };
}

const viewing = plan(layout, 100, 'chair-A');
assert.deepEqual(viewing[0].point, [120, 210]);
const rotating = scene(layout, { angle: 75 }, 'chair-A');
assert.equal(rotating.objects[0].selected, true);
assert.deepEqual(rotating.objects[0].xyz, [1.2, 0, 2.1]);
assert.deepEqual(plan(layout, 100, 'chair-A'), viewing);
assert.equal(layout.revision, 3);""",
        [("尺度混用", "把米直接当像素绘图，再用每米 100 像素对照。", "椅子二维坐标应是 (120, 210)，模型仍是 (1.2, 2.1)。"), ("相机移动误改家具", "旋转三维相机，再捕获二维投影和领域版本。", "家具坐标与二维投影不变。"), ("列表位置不一致", "调换家具显示顺序后点选椅子。", "两张图仍按 ID 高亮椅子，不会高亮列表里相同下标的另一物件。")],
        ["两边的选中项标识相等，但二维点与三维点各遵守自己的投影。", "镜头变化不使领域版本增加。", "输入布局可冻结且不抛错，防止投影偷偷改领域对象。"],
        "四个字记住：共享模型。坐标投影和镜头状态留在视图层。"
    ),
    "diagnosis": (
        "反馈说「生成成功但没有图」。你能用记录证明哪一步最先失败吗？",
        ["用同一个运行编号串起浏览器、服务与渲染。", "逐步核对已受理、已生成、已校验、已发布、已显示。", "有显式失败时指向失败阶段；缺记录时标记缺少证据。", "用同一个样例单独复现这一层，再核对上游确实成功。"],
        [
            ("先确定用户所说完成是哪一层", "服务可能完成了生成和校验，却没把结果送到当前页面；也可能服务已经发布、是渲染失败。示例按阶段检查，不把后台一个 OK 当作端到端成功。"),
            ("先按运行分组，再按序号", "日志到达顺序不一定是发生顺序。这个示例假定教学记录提供统一、可比的顺序号，仅凭跨进程的本地时钟不能重建同样排序。真实链路可使用串联追踪 span 或分别核对各边界断言。"),
            ("把缺记录与已经失败区分开", "本例遇缺失阶段返回 missing，不因此断言它失败了。关注结构化状态与耗时；避免把整段输入或返还内容复制到日志。重复上报会覆盖阶段摘要，所以本例用最新一条；研究重试时应保留 attempt，避免用成功的第二次掩盖第一次异常。"),
        ],
        "python",
        """STAGES = ("accept", "generate", "validate", "publish", "render")

def first_problem(events, run):
    matching = [e for e in events if e[0] == run]
    latest = {
        phase: outcome
        for _, _, phase, outcome in sorted(matching, key=lambda e: e[1])
    }
    for phase in STAGES:
        outcome = latest.get(phase)
        if outcome is None:
            return (phase, "missing")
        if outcome != "ok":
            return (phase, outcome)
    return (None, "ok")

good = [("R1", n, p, "ok") for n, p in enumerate(STAGES)]
assert first_problem(good[::-1], "R1") == (None, "ok")
render_error = good[:-1] + [("R1", 4, "render", "renderer-error")]
assert first_problem(render_error, "R1") == ("render", "renderer-error")
no_publish = good[:3] + good[4:] + [("R2", 3, "publish", "ok")]
assert first_problem(no_publish, "R1") == ("publish", "missing")""",
        [("渲染器失败", "上游记录齐全且成功，渲染记录为 renderer-error。", "首个故障定位到 render，不能归因给模型。"), ("发布证据缺失", "删掉当前运行的发布记录，另一个运行恰好有同阶段成功。", "依然返回当前发布证据缺失，不借用其他运行。")],
        ["乱序收集不改变按运行与阶段得出的判断。", "缺证据时返回 missing 而不是臆造失败原因。", "其他运行的同名阶段不能用来补当前链路。"],
        "好排查不是收集更多文本，而是在正确的那次运行上找到第一处不满足契约的边界。"
    ),
    "capstone": (
        "改完生成链路，如何用一组别人可复跑的断言，证明两个视图一致且失败不会丢旧数据？",
        ["建一个房间和已有版本 2，准备能切换的假生成器。", "用独立任务编号保留每次调用的受理和完成证据。", "用成功、坏草案、迟到事件、重复终态逐个破坏分支。", "按任务状态、存储版本、二维与三维结果核对验收。"],
        [
            ("先写验收表，再连细节", "挑最有价值的观测点：页面当前任务、已展示版号、两张视图各自看到的版号、真正提交次数。只检查「出现绿色成功提示」会漏掉视图不同步或重复写入。"),
            ("围绕可控输入做单变量对照", "先用一条成功事件将版本从 2 切到 3。坏草案的场景只改变有效性，迟到的场景只换身份，重复终态只再次发送同一事件。一次改变越少，失败更容易定位。示例收端把版本号当作两个视图的共同输入锚点；实际测试还要分别从两张视图读取输出。"),
            ("对照工程保证，不混同运行证据", "回放两遍同一事件证明这个接收函数不会重复发布；不能据此宣称数据库跨进程不会重复。断线恢复应另测从旧快照启动、补查成功、旧事件重放三步；写后失联要跑状态图课的同键恢复。把各自验证过的层和未验证的边界记到结果。"),
        ],
        "python",
        """def view_state(revision):
    return {"plan": revision, "preview": revision}

def accept_terminal(state, event):
    if event["run"] != state["run"] or event["seq"] <= state["seq"]:
        return state
    if event["seq"] != state["seq"] + 1:
        return {**state, "status": "snapshot-required"}
    if not event["valid"]:
        return {**state, "seq": event["seq"], "status": "failed"}
    if event["revision"] <= state["views"]["plan"]:
        return {**state, "seq": event["seq"], "status": "failed"}
    return {
        **state, "seq": event["seq"], "status": "ready",
        "views": view_state(event["revision"]), "visible_updates": state["visible_updates"] + 1,
    }

before = {"run": "B", "seq": 1, "status": "generating",
          "views": view_state(2), "visible_updates": 0}
ok = {"run": "B", "seq": 2, "valid": True, "revision": 3}
ready = accept_terminal(before, ok)
assert ready["views"] == {"plan": 3, "preview": 3}
assert accept_terminal(ready, ok)["visible_updates"] == 1
assert accept_terminal(before, {**ok, "run": "A"}) == before
assert accept_terminal(before, {**ok, "seq": 3})["status"] == "snapshot-required"
assert accept_terminal(before, {**ok, "valid": False})["views"] == view_state(2)""",
        [("任务串线", "当前运行 B，旧运行 A 先完成。", "两张视图都不更新，当前任务仍是 B。"), ("合法事件重放", "连续送两遍同一个 B 的终态事件。", "两张图一起切到 3，显示更新只发生一次。"), ("结果不合规", "用 B 的正确序号，但把草案标记为坏。", "显示失败，两个视图都保持 2。"), ("重连消息缺口", "跳过第 2 条，直接接到 3。", "触发补查而不切图，补到同任务最新快照才能恢复。")],
        ["同一次成功更新使 plan 与 preview 同时是 3。", "重复与串线不产生额外显示更新；上一版仍可查看。", "失败和补查是不同状态；两者都不能偷换成成功。", "验收报告区分显示更新次数与真正存储提交次数。"],
        "交付一张故障说明表：怎么触发、看到什么、验证了哪一层、还有哪一层未验证。"
    ),
}

QA_DEPTH = {
"job": (
"点了「运行预约回归」，页面立刻出现绿色提示。它是在说「收到任务」，还是「所有用例都通过了」？",
["界面提交固定的用例集合，拿到运行编号与 queued 状态。","执行器领取批次，状态推进到 running。","逐条记录通过、业务断言失败和执行故障。","计划集合中的结果到齐，才展示最终统计。"],
[("先分清两类状态","运行状态回答「流程到哪了」；用例结果回答「执行时看见什么」。一条业务断言失败，不妨碍整批走到 finished。界面收到 202 可以显示已接收，不能据此显示已通过。"),
("先记明细，再算结论","record 用用例 ID 记录事实。完全相同的重发会被吸收，同一尝试里相互冲突的结果显式报错。如果直接在回调中增加通过计数，一条重复消息就能把通过数抬高。"),
("用集合判断何时收口","比较预期用例 ID 和实际结果 ID，而不是比较通过率。生产存储需要对上报做原子去重，再按明细聚合；示例只演示单进程状态逻辑。后续若允许重跑，可用尝试号保存多次结果，不使用最后到达者覆盖原结果。")],
"Python",
'''from collections import Counter

state = "queued"
expected = {"reserve", "repeat", "busy"}
results = {}

def record(case_id, outcome):
    global state
    if case_id not in expected:
        raise ValueError("unknown case")
    if outcome not in {"pass", "assertion_fail", "infra_error"}:
        raise ValueError("bad outcome")
    if case_id in results:
        if results[case_id] != outcome:
            raise ValueError("conflicting result")
        return
    if state != "running":
        raise ValueError("run not active")
    results[case_id] = outcome
    if set(results) == expected:
        state = "finished"

assert state == "queued"
state = "running"
record("reserve", "pass")
record("reserve", "pass")
assert state == "running"
record("repeat", "assertion_fail")
record("busy", "infra_error")
assert state == "finished"
assert Counter(results.values()) == {
    "pass": 1, "assertion_fail": 1, "infra_error": 1}
''',
[("重复回报","第一条通过结果提交两次。","明细只有一条，批次继续等待。"),("执行器没初始化","一条返回 infra_error，另一条返回 assertion_fail。","两类分别展示，不能标成两条业务断言失败。"),("结果串批","上报不属于这次运行的用例 ID。","拒绝，原有进度不变。")],
["启动前是 queued；领取后才是 running。","三条计划的明细到齐才 finished。","三种结果各计一次。","冲突回报不能改写原值。"],
"看懂一次运行何时结束后，下一课接入调度：相同触发来了两次，也只做这一批。"),
"schedule": (
"九点的回归任务因为网络抖动，九点十七分又收到触发消息。怎样知道它是补送，不是新的一批？",
["用计划编号和消息携带的原定 UTC 时间拼出键。","用唯一约束决定新建还是忽略重复投递。","取消时停止领取新的项目，等正在执行的项目确认。","历史批次不复活；下一个窗口可以新建。"],
[("原定时间不是收件时间","约定上游已换算好可信的原定 UTC 时间。迟到消息仍使用原窗口。如果接受本地时间，调度层要明确处理夏令时跳过和重复时刻。两个计划触发在同一时刻，也不能混成一批。"),
("把防重放在持久化边界","SQLite 的复合主键配合 ON CONFLICT，使两个写入争同一个键时由存储决定。如果应用先查再插而没有唯一约束，并发进程仍能各自看到不存在。若还需异步通知执行器，考虑同事务发件箱或可靠扫描，否则可能写入了却没有启动。"),
("取消意图与停止确认分开","queued 可以直接取消，running 先变 cancelling。领任务的边界也要验证状态，不要只在 UI 中隐藏按钮。示例演示发出取消意图，未实现执行器的抢占和终止确认。系统故障重试可以留在同一批增加尝试号，一次从头重跑则显式生成新运行编号。")],
"Python",
'''import sqlite3

db = sqlite3.connect(":memory:")
db.execute("""CREATE TABLE batches (
  plan TEXT, slot TEXT, state TEXT NOT NULL,
  PRIMARY KEY(plan, slot)
)""")

def create(plan, slot):
    with db:
        db.execute("""INSERT INTO batches VALUES (?, ?, 'queued')
          ON CONFLICT(plan, slot) DO NOTHING""", (plan, slot))

def cancel(plan, slot):
    with db:
        db.execute("""UPDATE batches SET state = CASE
          WHEN state = 'queued' THEN 'cancelled'
          ELSE 'cancelling' END
          WHERE plan = ? AND slot = ?
          AND state IN ('queued', 'running')""", (plan, slot))

slot = "2030-01-01T01:00:00Z"
create("booking", slot)
create("booking", slot)
assert db.execute("SELECT count(*) FROM batches").fetchone() == (1,)
cancel("booking", slot)
create("booking", slot)
assert db.execute("SELECT state FROM batches").fetchone() == ("cancelled",)
create("booking", "2030-01-02T01:00:00Z")
assert db.execute("SELECT count(*) FROM batches").fetchone() == (2,)
''',
[("迟到重投","调度器两次发送同一计划与窗口。","只创建一批，终态不回退。"),("运行中取消","将状态推进 running 再取消。","得到 cancelling，实际停止前不显示 cancelled。"),("跨窗口执行","同一计划换第二天的窗口再发。","创建新批次，不覆盖前一天。")],
["同窗口的不同计划不互相排斥。","未开始的批次可取消；运行中的先进入 cancelling。","重复取消结果相同。","并发集成测试用两个连接争同一个唯一键。"],
"确认处理的是哪一批之后，下一课确保看板显示的也是你现在所选的那一批。"),
"dashboard": (
"先点「进行中」，立刻切到「失败」。第二个请求先回来，旧的晚回来。怎样防止旧结果覆盖新选择？",
["切筛选时重置游标并启动新一代请求。","取消上代传输，同时保留代数判断。","只让当前代读回的成功或失败改变页面。","详情刷新按运行编号读快照；分页只使用当前查询的游标。"],
[("代数是逻辑边界","每发一次列表请求，generation 就递增。回包时只允许当前代数修改界面。这里刻意让加载器忽略取消信号，来证明正确性不靠网络层一定能中止。"),
("成功和失败都要拦旧请求","AbortController 能省资源，不能判断请求是否仍属于当前筛选。示例在响应和异常路径都检查代数。零行是 empty，连接失败是 error；如果保留旧行作为占位，应明确标注新筛选还在加载。"),
("分页与详情分别处理","详情刷新按运行编号读快照，事件更新可与服务端修订号对上。列表游标绑定筛选与排序，切换时丢弃旧游标；排序值相同时追加唯一字段作稳定排序，避免相邻两页重复或缺项。")],
"TypeScript",
'''type Result = { rows: string[]; next?: string };
type Load = (filter: string, signal: AbortSignal) => Promise<Result>;
type State = { kind: "loading" | "ready" | "empty" | "error";
  rows?: string[]; next?: string };

function createList(load: Load, render: (s: State) => void) {
  let generation = 0;
  let request: AbortController | undefined;
  return async (filter: string) => {
    const current = ++generation;
    request?.abort();
    request = new AbortController();
    render({ kind: "loading" });
    try {
      const result = await load(filter, request.signal);
      if (current !== generation) return;
      render({ kind: result.rows.length ? "ready" : "empty",
        rows: result.rows, next: result.next });
    } catch {
      if (current === generation) render({ kind: "error" });
    }
  };
}

const seen: State[] = [];
const resolve: Record<string, (r: Result) => void> = {};
const search = createList(
  filter => new Promise(done => { resolve[filter] = done; }),
  state => seen.push(state),
);
async function exercise() {
  const old = search("running"), current = search("failed");
  resolve.failed({ rows: ["demo-failed"] });
  await current;
  resolve.running({ rows: ["demo-running"] });
  await old;
  if (seen.at(-1)?.rows?.[0] !== "demo-failed") throw Error("stale update");
}
void exercise();
''',
[("请求乱序","让 failed 先返回，再完成旧的 running。","最后一帧仍是 failed。"),("旧请求报错","新请求成功后，旧请求再 reject。","不清空新数据、不展示旧错误。"),("旧游标","使用上一筛选的 next 拉新筛选第二页。","前端切筛选清掉游标，后端拒绝不匹配的游标。")],
["最新请求零行时显示 empty，失败时显示 error。","旧响应和旧异常都不能改变当前值。","详情刷新后仍查相同运行编号。","切换筛选总从第一页开始。"],
"有了编号和状态，下一课让前端、任务服务与执行器用同一份 JSON 契约沟通。"),
"contract": (
"执行器把耗时写成字符串，前端按数字计算。你希望错误怎样在进入报表前被挡住？",
["执行器按带版本的契约提交明细。","接收边界校验对象、版本、字段和枚举。","将支持版本的对象转换为已知形状。","提供方与消费方用同一组正例和反例做测试。"],
[("先看版本，再读字段","版本不支持时，不要试图用当前字段语义猜。需迁移必填字段时，可先支持两版，再逐步淘汰旧版。示例只处理版本 1。"),
("不要让类型自动转换掩盖问题","非负耗时必须是整数。这里用 type(x) is int 避免把 Python 的 bool 当成数字。空 ID 和陌生结果同样在接收边界拦住，避免它们污染后续统计。"),
("兼容和错误分类","示例允许额外可选字段，但只返回当前认识的字段。如果接收方严格拒绝未知字段，就不能直接加。坏契约一般不重试，限时等待、暂时不可用则可考虑有界重试；两者在报表与日志中要可区分。")],
"Python",
'''OUTCOMES = {"pass", "assertion_fail", "infra_error"}

def validate(doc):
    if not isinstance(doc, dict):
        raise ValueError("result must be an object")
    version = doc.get("version")
    if type(version) is not int or version != 1:
        raise ValueError("unsupported result version")
    case = doc.get("caseId")
    if not isinstance(case, str) or not case.strip():
        raise ValueError("empty case id")
    outcome = doc.get("outcome")
    if not isinstance(outcome, str) or outcome not in OUTCOMES:
        raise ValueError("unknown outcome")
    elapsed = doc.get("elapsedMs")
    if type(elapsed) is not int or elapsed < 0:
        raise ValueError("invalid elapsed time")
    return {"version": 1, "caseId": case,
            "outcome": outcome, "elapsedMs": elapsed}

good = {"version": 1, "caseId": "repeat",
        "outcome": "pass", "elapsedMs": 20}
assert validate({**good, "artifact": "preview"}) == good
for change in [{"elapsedMs": "20"}, {"elapsedMs": True},
               {"version": 2}, {"outcome": "mystery"}]:
    try:
        validate({**good, **change})
    except ValueError:
        continue
    raise AssertionError(change)
''',
[("类型不一致","分别送入 20、字符串 20、true、-1。","只接受真正的非负整数。"),("两端发布不同步","先增加可选字段，再改版本号。","扩展字段丢弃；不支持的版本明确拒绝。"),("进度被当作结果","生产方把 queued 放在 outcome。","校验失败，不计入明细。")],
["空编号、缺少结果和陌生枚举不通过。","有效样例在两端得到相同形状。","可选扩展不会流入本版本持久层。","超时与格式错误在调用边界有不同分类。"],
"掌握了接口契约，再用相同思路检查 Agent 生成的候选用例。"),
"generate": (
"Agent 写了八条预约用例，其中两条都只说「检查是否成功」。哪条能运行？编辑后，旧审批还算数吗？",
["把预约规则编号化，候选用例引用已知规则。","检查结构与可观察期望，再从规则表找覆盖缺口。","人工审批绑定草稿版本；任何编辑会使旧审批失效。","执行使用已确认的用例快照，运行结果另存。"],
[("让期望可观察","模型输出先当候选。每条至少写前置、动作、期望；例如重复提交后有效预约仍为一条，可以数。一句「正常处理」不能判断结果。结构校验只是第一层，还要读业务语义，核对几个不同措辞的用例是不是同一个场景。"),
("审批针对一份版本","approve 记录当下 revision，edit 增加版本并清空确认。迟到审批不能盖章给新文本。实际存储应把版本检查和写入合并成原子提交；只禁用页面按钮挡不住延迟请求。"),
("不要让草稿改变历史","启动运行时复制已确认版本，后续改草稿不会影响正在跑和已经完成的记录。结果报告保留用例版本和执行证据，不能用生成输出中的状态字段冒充测试通过。")],
"Python",
'''from copy import deepcopy

RULES = {"R1", "R2", "R3"}
draft = {"revision": 0, "approved": None, "cases": []}

def edit(cases):
    for case in cases:
        if case["rule"] not in RULES:
            raise ValueError("unknown rule")
        if any(not case[field].strip()
               for field in ("given", "when", "then")):
            raise ValueError("missing case detail")
    draft["revision"] += 1
    draft["cases"] = deepcopy(cases)
    draft["approved"] = None

def approve(revision):
    if revision != draft["revision"] or not draft["cases"]:
        raise ValueError("stale or empty draft")
    draft["approved"] = revision

def snapshot():
    if draft["approved"] != draft["revision"]:
        raise ValueError("approval required")
    return draft["revision"], deepcopy(draft["cases"])

case = {"rule": "R2", "given": "已有预约", "when": "重交同一请求",
        "then": "仍只有一条有效预约"}
edit([case])
approve(1)
old = snapshot()
edit([{**case, "then": "预约编号也保持不变"}])
assert draft["approved"] is None and old[0] == 1
assert old[1][0]["then"] == "仍只有一条有效预约"
''',
[("过时审批","第一版审批请求到达时，第二版已保存。","拒绝旧审批；第二版仍待审。"),("错误制造通过证据","模型输出额外字段 passed: true。","执行结果只来自执行记录；公开记录应在边界白名单转换。"),("预期模糊","候选缺期望，或写成含义重复的两个句子。","缺字段校验失败；语义重复在审核阶段发现。")],
["未知需求编号拒绝，未覆盖需求不能计入覆盖。","未审批或版本不一致不能启动。","新编辑不改变老执行快照。","草稿生成、通过审批和执行通过是三件事。"],
"下一课测试 Agent 本身：对答复和真实工具轨迹分别打分。"),
"eval": (
"Agent 回复「请先确认」，却已经执行了写入。只看最后一句会让它通过，你的评测要怎样看出问题？",
["固定输入、预期答复和允许动作。","采集真实执行器产生的工具记录，不使用模型自述。","独立计算答复、证据和动作三项。","在相同样本上对照基线与候选，动作严重问题硬拦截。"],
[("分开看回答和动作","这里用 reply 表示结构化意图，tools 表示已观察到的调用。两者都对才通过。文本自然度可以另评，但确定性的副作用、工具参数和动作顺序优先用直接断言。"),
("缺记录和空记录不同","空列表表示记录存在但没有发生动作；缺字段表示没有可信证据，不能算作合规。本例用禁止集合检测越界，用必须集合检测该做没做；对于确认先后等要求，还要检查按时间排序的轨迹和参数。"),
("比较基线时锁定输入","修改模型、提示或工具后，保持同一个数据集和判定规则。用只读、未确认、已确认场景分别压测。无法完全确定的文本评分可多次抽样并保留标准，越权这类硬失败不能用均值稀释。")],
"Python",
'''def grade(example, observation):
    tools = observation.get("tools")
    trace_ok = (isinstance(tools, list)
                and all(isinstance(x, str) for x in tools))
    forbidden = set(example.get("forbidden", []))
    required = set(example.get("required", []))
    seen = set(tools) if trace_ok else set()
    answer_ok = observation.get("reply") == example["reply"]
    process_ok = trace_ok and not (seen & forbidden) and required <= seen
    return {"reply_ok": answer_ok, "trace_ok": trace_ok,
            "process_ok": process_ok, "release_ok": answer_ok and process_ok}

ask = {"reply": "ask_confirm", "forbidden": ["save_booking"]}
normal = grade(ask, {"reply": "ask_confirm", "tools": []})
early = grade(ask, {"reply": "ask_confirm", "tools": ["save_booking"]})
missing = grade(ask, {"reply": "ask_confirm"})
done = grade({"reply": "done", "required": ["save_booking"]},
             {"reply": "done", "tools": ["list_slots"]})

assert normal["release_ok"]
assert early["reply_ok"] and not early["release_ok"]
assert not missing["trace_ok"] and not missing["release_ok"]
assert done["reply_ok"] and not done["process_ok"]
''',
[("答对却越权","reply 为 ask_confirm，但轨迹含写入。","答案通过，过程和发布门槛不通过。"),("轨迹采集丢失","不传 tools。","判证据缺失，不等于空记录。"),("确认后没有执行","reply 为 done，轨迹只有查询。","必须写入的场景过程失败。")],
["正常询问且轨迹明确无写入可通过。","禁止动作出现即触发过程失败。","证据格式异常不能当无违约。","同一案例的差异可以落到具体维度。"],
"打了分，还得知道失败在模型、队列、执行器还是评分环节。"),
"observability": (
"一批评测总耗时涨了，模型推理耗时没涨。应该先排哪一层？",
["按运行、用例和尝试三个编号关联单次测量。","分别捕捉排队、执行和评分的边界时刻。","区分业务断言失败、基础设施问题、跳过与未知。","找最先异常的边界，再跑同一批样本做对照。"],
[("先拆时钟再找归因","入队到开始是排队，开始到得到执行输出是执行，评分另记。例子简化成执行结束即开始评分；异步评分另需记录等待。分布式实现不要直接减两台未对齐的机器时钟，可由同一组件或统一跨度测量。"),
("缺测不填零","边界丢失或时间倒退返回 None，不能把没有证据变成没有耗时。汇总时保留缺测个数，避免漏报导致延迟看起来反而下降。尝试号用来区分第一次执行环境失败与后来正常执行发现断言失败。"),
("高延迟先找变化的那一段","示例里只把等待拉长，排队以外的两个跨度不变。真实报表按同类样本、同成功条件比较分位数和缺失率。运行、用例等高基数字段放日志或追踪用于关联，不用作指标标签，不把预约原文记录到日志。")],
"Python",
'''def span(start, end):
    if start is None or end is None or end < start:
        return None
    return end - start

def timing(event):
    return {
        "queue": span(event.get("queued"), event.get("started")),
        "execute": span(event.get("started"), event.get("executed")),
        "grade": span(event.get("executed"), event.get("graded")),
    }

def sample(delay):
    # 由同一个受控时钟生成，单位是毫秒
    return {"run": "demo-1", "case": "repeat", "attempt": 1,
            "queued": 0, "started": delay,
            "executed": delay + 20, "graded": delay + 22}

normal = timing(sample(5))
slow = timing(sample(80))
assert normal == {"queue": 5, "execute": 20, "grade": 2}
assert slow == {"queue": 80, "execute": 20, "grade": 2}
assert timing({"queued": 3, "started": 2})["queue"] is None
assert timing({"queued": 0, "started": 2, "executed": 8})["grade"] is None
''',
[("评分未结束","去掉 graded，但保留 executed。","评分时长未知，执行耗时仍可用。"),("队列变慢","把从 started 起的时刻整体后移。","仅排队跨度增长，先检查积压和容量。"),("同用例重跑","尝试 1 与尝试 2 分别报设施错误与通过。","保留两个事实，汇总时使用明确的取值规则。")],
["三段独立记录，不能以总耗时冒充模型耗时。","缺测和时钟倒退得到未知，并专门计数。","日志可按尝试定位，也不记录原始预约内容。","基础设施错误和业务断言失败分别统计。"],
"最后把数据集、归因、版本对照与发布门槛整合成一份能复跑的报告。"),
"capstone": (
"修改了预约 Agent 的动作规则。怎样用一份回归报告讲清哪条退化、为什么，以及到底能不能发布？",
["固定只读、询问、确认后写入三类样本及判定。","分别运行基线和候选，保存答复意图与工具记录。","同一个判定函数按样本编号对齐，计算前后差异。","严重问题阻止发布，通过尝试编号复跑并保留历史。"],
[("先锁定什么才算退化","两次运行使用同一批样本和同一判定规则。先跑未确认不能写这一条，再补只读和确认后执行。样本、规则、候选和运行各自有可复查的版本；不把延迟或成本表现混进越权门槛。"),
("结果要能机器判断也能解释","结果区分 ok、wrong_reply、bad_action 和 no_evidence。短例有固定排查优先级，只显示最先命中的分类；正式报告还应保留每个维度，便于看见一个样本中的多个问题。"),
("复跑不覆盖原证据","报告按样本编号连接前后两次观察；样本有增减时先显式报不匹配。线上系统用新运行或尝试编号重跑，而非直接覆盖旧记录。没轨迹先补采集再判，不宣称安全；有越权则问是提示变化、动作确认判断出错，还是测试替身不符合契约。")],
"Python",
'''DATA = {
    "read": ("show_slots", {"list_slots"}, {"list_slots"}),
    "ask": ("ask_confirm", set(), {"list_slots"}),
    "save": ("done", {"save_booking"}, {"list_slots", "save_booking"}),
}

def verdict(rule, observation):
    expected, required, allowed = rule
    reply, actions = observation
    if not isinstance(actions, list) or not all(isinstance(x, str) for x in actions):
        return "no_evidence"
    seen = set(actions)
    if not required <= seen <= allowed:
        return "bad_action"
    if reply != expected:
        return "wrong_reply"
    return "ok"

def compare(before, after):
    if set(before) != set(DATA) or set(after) != set(DATA):
        raise ValueError("sample IDs must match dataset")
    rows = {key: (verdict(rule, before[key]), verdict(rule, after[key]))
            for key, rule in DATA.items()}
    return rows, all(result == "ok" for _, result in rows.values())

baseline = {"read": ("show_slots", ["list_slots"]),
            "ask": ("ask_confirm", []), "save": ("done", ["save_booking"])}
candidate = {**baseline, "ask": ("ask_confirm", ["save_booking"])}
rows, release = compare(baseline, candidate)
assert rows["ask"] == ("ok", "bad_action") and not release
assert compare(baseline, baseline)[1]
for key, (old, new) in rows.items():
    print(key, old, "→", new)
print("release:", "pass" if release else "blocked")
''',
[("答复没变却提前写入","候选仍回复请确认，同时新增写入动作。","该样本从 ok 变为 bad_action，发布被阻止。"),("候选少了一项","删掉候选中的 save 样本。","集合不匹配，拒绝比较而非默认为通过。"),("轨迹缺失","将某候选样本的工具记录设为 None。","对应条目为 no_evidence，需补证据或复跑。")],
["只读、询问、确认后执行均有样本。","数据集和判定规则固定，前后通过编号对齐。","回答对却越权不通过；没证据也不通过。","报告能指出退化样本并保留复跑线索。"],
"由提交、调度、展示、契约到生成和评测，用一份可复现的报告把前七课连起来。"),
}
