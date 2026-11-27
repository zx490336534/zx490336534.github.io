"""Original CaseLab worked examples. Each snippet runs with the Python standard library."""

CASELAB_EXTRA = {}
def add(key, title, minutes, goal, scene, term, answer, distractor, steps, question, walkthrough, code, failures, checks, takeaway):
    correct = len(CASELAB_EXTRA) % 2
    choices = [answer, distractor] if correct == 0 else [distractor, answer]
    overview = (key, title, minutes, goal, scene, steps[:3], code.splitlines()[0],
                "运行代码里的断言，然后只改一个输入，复现「" + failures[0][0] + "」。先写预期再运行。",
                question, choices, correct, takeaway)
    CASELAB_EXTRA[key] = (overview, term, (question, steps, walkthrough, "Python", code, failures, checks, takeaway))


add("test-layers", "测试分层：用最短的路径发现缺陷", 22,
    "对同一个预约问题，分别设计单元、契约和端到端测试。",
    "13:00 的预约接受了长度为零的区间；改完校验后，页面还必须显示可理解的失败原因。",
    ("测试分层", "把规则本身、跨边界约定和用户可见流程各自验证，不要求每个场景都穿完整链路。"),
    "用单元测试钉边界，契约钉错误字段，端到端只保留关键可见路径", "给每个时间输入都配一条端到端测试",
    ["调用规则函数验证零长度与相邻区间。", "从入口读标准错误形状，不检查内部类名。", "运行一个从点击到界面反馈的流程。", "为变化最大、最难定位的那层保留证据。"],
    "预约规则和页面提示同时变化时，测试该放在哪几层？",
    [("单元测试是用来穷举变化的","时间区间、默认值和布尔条件由纯函数判定，覆盖相等、相邻、跨分界这几种情况。规则模型不应该关心按钮布局或 HTTP 状态，可用直接参数快速定位回归。"),
     ("契约是跨边界的最小共同语言","入口把拒绝映射为稳定的 code。端到端不适合替代结构校验：界面可能恰好用兜底提示，掩盖协议字段已经漂移。测试不要断言整段错误文案，那属于展示层。"),
     ("这里的 E2E 是内存全流程","示例点按钮模拟页面消费入口响应，未启动浏览器。真实 E2E 至少增加一个浏览器脚本，验证点击、提交、状态更新和提示展示，避免把代理函数冒充浏览器证据。")],
    '''def valid(start, end):
    return 0 <= start < end <= 24

def route(start, end):
    if not valid(start, end):
        return 422, {"code": "BAD_INTERVAL"}
    return 201, {"id": "demo-booking"}

def click_submit(start, end):
    status, body = route(start, end)
    messages = {"BAD_INTERVAL": "结束时间须晚于开始"}
    return "预约成功" if status == 201 else messages[body["code"]]

# 单元：把相等边界钉住
assert not valid(13, 13)
assert valid(13, 14)
assert not valid(23, 25)

# 契约：不关心页面长什么样
assert route(13, 13) == (422, {"code": "BAD_INTERVAL"})

# 内存 E2E：保留用户可见的成功和失败各一条
assert click_submit(13, 13) == "结束时间须晚于开始"
assert click_submit(13, 14) == "预约成功"
''',
    [("零长度被接纳","把 start < end 改为 start <= end。","边界单元断言失败，随后入口和展示断言也暴露影响。"),("契约漂移","把错误字段从 code 改为 reason，保持值不变。","契约先失败，界面也无法映射错误；修边界不是改业务规则。")],
    ["合法半开区间可提交。","规则相等边界被拒绝。","协议错误有机器可读码。","用户能看见友好提示。"],
    "原则不是一味减少端到端，而是在最小可诊断的边界验证规则，再用关键路径保护整合结果。")

add("replay-fixtures", "测试夹具：把时间、随机数和依赖固定下来", 23,
    "为限时预约构造可重复的输入和外部响应。",
    "某条临近过期的用例只有夜间偶尔失败；另一个开发者本地完全复现不出。",
    ("测试夹具", "把某个测试场景的初始状态、依赖输入和结束清理清楚地封装起来。"),
    "传入假时钟和固定依赖，重放时同时核对调用请求", "让测试每晚固定时刻才跑",
    ["列出不受业务控制的时间、随机数与第三方结果。", "把时间和响应通过接口传入纯逻辑。", "记录请求形状并严格匹配重放的下一步。", "固定时钟只用于测试，生产的时区和响应改变另测。"],
    "怎样稳定复现恰好在过期边界的失败？",
    [("边界直接驱动","把当前时间变成参数，写出 expires-1 与 expires 两个场景。不需要 sleep。示例中到期时间点本身视为无效，和 UI 显示精度无关。"),
     ("重放不等于允许任何调用","重放器验证调用槽位、次数和顺序。缺记录时不返回假成功；调用结束后也检查没有剩余响应。这能抓住多做一次、少做一次或换错参数。"),
     ("合成数据不带历史包袱","夹具每次从干净状态构造，不用共享可变列表。若要检查真实适配器格式，可运行合约烟测，但不要指望内存重放覆盖网络异常或时区转换。")],
    '''from collections import deque

def replay(records):
    pending = deque(records)
    def lookup(slot):
        if not pending:
            raise AssertionError("unexpected extra call")
        requested, seats = pending.popleft()
        assert slot == requested
        return seats
    return lookup, pending

def may_book(now, expires, lookup):
    if now >= expires:
        return False
    return lookup("slot-b") > 0

lookup, pending = replay([("slot-b", 1)])
assert may_book(119, 120, lookup)
assert not pending

lookup, pending = replay([])
assert not may_book(120, 120, lookup)
assert not pending
''',
    [("边界错一秒","把到期判断改成 now > expires。","恰好到期会意外查座位，重放器拒绝额外调用。"),("参数串了","把查询换成 slot-x。","记录中的下一步与请求不匹配，测试失败。")],
    ["同一夹具反复重放得到相同结果。","运行时钟和测试时钟使用同一个业务入口。","过期时不发外部请求。","夹具使用后检查无未消费记录。"],
    "稳定复现比盲目重跑更有价值。固定外部变量，也要检查实际依赖调用是否仍符合约定。")

add("worker-retries", "执行器重试：有预算、有分类、有幂等", 27,
    "为暂时性失败设计有上限的重试，保留第一次的错误证据。",
    "写预约时，服务端成功保存但响应丢了；执行器重试如果用新编号，就会多写一条。",
    ("幂等键", "重试仍携带同一个逻辑操作标识；接收方把同一标识与请求内容绑定，只承认一次副作用。"),
    "暂时故障才重试；每次使用相同键并限制预算", "任何错误都立即无限重试",
    ["先划分终态错误和暂时错误。","给请求分配稳定的逻辑标识。","预算内按计划等待后再尝试，并保留失败分类。","服务确认重复写只是取回旧结果。"],
    "写成功但响应丢失，执行器应该怎样恢复？",
    [("把失败细分成可重试和不可重试","输入验证不该重试，网络超时可重试但不表示未发生写入。有限次数以包含首次调用的总尝试数表示；示例显式记录等待预算但不实际睡眠。"),
     ("谁来保证不重写","执行器传 stable-key，接收服务要持久化键与请求内容，拒绝同键不同内容。内存 dict 只说明行为，真实实现要用可靠存储和事务保护目标操作与幂等记录。"),
     ("预算、分类与抖动","生产中也设总截止时间，叠加退避和少量随机抖动，避免多个执行器同步施压。把预算耗尽硬失败和业务拒绝分别计入报告；不要因为最终成功而抹掉第一次响应丢失。")],
    '''class Transient(Exception):
    pass

saved, attempts, delays = {}, [], []

def write(key, value):
    attempts.append(key)
    if key in saved:
        if saved[key] != value:
            raise ValueError("idempotency conflict")
        return saved[key]
    saved[key] = value
    raise Transient("response lost after commit")

def run(key, value, max_attempts=3):
    for i in range(max_attempts):
        try:
            return write(key, value)
        except Transient:
            if i + 1 == max_attempts:
                raise
            delays.append(2 ** i)
    raise ValueError("empty retry budget")

assert run("demo-key", "slot-1") == "slot-1"
assert len(saved) == 1
assert attempts == ["demo-key", "demo-key"]
assert delays == [1]
''',
    [("提交成功却无回执","首次保存后抛暂时错误。","第二次返回同一结果，不新增预约。"),("同键不同载荷","把预约槽位改掉但使用原键。","拒绝并停止重试；原值仍在。")],
    ["暂时错误不等于没有副作用。","同键同载荷得到同一结果。","预算设为一时不发第二次请求。","逻辑操作重复提交不会多一条记录。"],
    "重试只是重新尝试拿到结果；把潜在副作用和状态冲突当成一等问题处理。")

add("worker-leases", "租约与围栏号：让接手者成为唯一写者", 25,
    "阻止失效执行器提交迟到的结果。",
    "A 工作器领取回归后断网，租约过期由 B 接手。A 随后恢复网络并提交旧结果。",
    ("围栏号", "每次重新领取都发更大的编号；写入端拒绝不再拥有当前编号的执行器。"),
    "令结果存储检查当前围栏号", "仅检查执行器 A 的操作耗时是否大于平均",
    ["写入任务租约记录和递增编号。","到期时由新执行器领取新编号。","期满或编号失效的写入被拒绝。","所有时间和编号都以持久化边界为准。"],
    "只靠心跳监控，能防止失联执行器写入迟到结果吗？",
    [("心跳只说明活跃，不能撤销旧进程","旧进程本身可能还在运行。领取时读当前时钟、比较到期时间、递增编号。每次回报都携带这个编号，持久化接受当前且有效的领取。"),
     ("先检查租约，再修改结果","示例使用独立计时参数，真实写入需要原子检查与更新。数据库可用条件更新并检查影响行数；只在 Worker 内判断当前号，不能防止另一台机器已经接手。"),
     ("对外部副作用要单独处理","围栏保护的是支持围栏检查的存储。外部服务不接围栏时，还需要单独的幂等、授权状态和补偿策略；本例不保证随意一段脚本的全部副作用都被撤销。")],
    '''job = {"token": 0, "expiry": 0, "result": None}

def claim(now, ttl):
    if job["result"] is not None or job["expiry"] > now:
        return None
    job["token"] += 1
    job["expiry"] = now + ttl
    return job["token"]

def commit(token, now, result):
    if token != job["token"] or now >= job["expiry"]:
        return False
    if job["result"] is not None:
        return False
    job["result"] = result
    return True

a = claim(0, ttl=5)
assert a == 1 and claim(3, ttl=5) is None
b = claim(5, ttl=5)
assert b == 2
assert not commit(a, 6, "stale")
assert commit(b, 6, "current")
assert not commit(b, 7, "duplicate")
assert job["result"] == "current"
''',
    [("僵尸执行器","A 取编号 1，B 接手后 A 仍提交。","拒绝 A，保留 B 写入的值。"),("租约到期点","在 now == expiry 时提交。","旧执行器落在有效期外，不得更新。")],
    ["租约未到期时不可重复领取。","每次真正接手续发严格递增的围栏号。","相同围栏号第二次提交不覆盖。","完成任务不再被重新领取。"],
    "判断当前谁有权写结果，要靠存储可检查的凭证，不靠执行器自觉。")

add("worker-cancel", "取消不是关进程：如何表示已经开始的工作", 22,
    "让取消请求停住后续工作，又不误报已经发生的结果。",
    "预约回归已派发一个项目，用户点取消；一个队列项正好同时被执行器领取。",
    ("协作取消", "系统记录取消意图，执行器在安全检查点读到后停止启动后续工作，并确认已在跑的工作真正收口。"),
    "记录意图，阻止新领取，收口时依据已保存事实", "点击取消后立即删除所有明细",
    ["原子记录取消意图。","执行器每次领取前检查取消状态。","已开始的项提交结果或确认停止。","未开始项标为跳过，已经记录的结果保留。"],
    "页面能在用户点下取消后立刻承诺「所有副作用已撤销」吗？",
    [("取消的是未来工作","任务没有开始时可直接结束；运行中需要先标请求已接收。这里捕捉任务级状态及项级状态，示例保留已完成项，并给未被启动的项贴 skipped。"),
     ("检查点与副作用之间有窗口","如果下一项领取和取消发生竞速，要在同一原子边界控制。对已经完成的外部动作，取消只阻止以后发生的动作，不能回滚过去；若需要撤销，用独立补偿操作并记录结果。"),
     ("停止确认是一个可观测事实","界面区分 cancelling 与 cancelled。队列运行者失联时不能凭空声称已停止；保留未知状态和超时告警。示例把当前正在执行的项目结果视为晚到的真实事实，不试图删除。")],
    '''todo = ["a", "b", "c"]
active = set()
finished = {}
cancelled = False

def claim():
    if cancelled or not todo:
        return None
    item = todo.pop(0)
    active.add(item)
    return item

def done(item, outcome):
    if item not in active:
        raise ValueError("item was not active")
    active.remove(item)
    finished[item] = outcome

def outcomes():
    skipped = {item: "skipped" for item in todo} if cancelled else {}
    return {**finished, **skipped}

def snapshot():
    if cancelled:
        return "cancelling" if active else "cancelled"
    return "running" if active or todo else "finished"

assert claim() == "a"
cancelled = True
assert snapshot() == "cancelling" and claim() is None
done("a", "pass")
assert snapshot() == "cancelled"
assert outcomes() == {"a": "pass", "b": "skipped", "c": "skipped"}
''',
    [("还有正在执行项","在 a 已领取后取消，再模拟 a 报回成功。","停止领取 b、c；保留 a 的成功。"),("重复上报已结束项","对 a 调两次 done。","后一次拒绝，不重复计数。")],
    ["取消后 claim 不再返回任何新项。","执行器确认之前状态是 cancelling。","取消保留已经确认的副作用与结果。","未领取项与断言失败分开显示。"],
    "取消是有顺序的状态变化；写对中间状态，报告才不会对正在执行的工作撒谎。")

add("test-selection", "测试选择与覆盖：改了什么，最少要重跑什么", 22,
    "按影响边界构建用例选择器，未知改动默认扩大范围。",
    "团队把预约价格改成区间计算，一次改动可能触发金额、确认和付款结果。",
    ("变更影响图", "从业务区域到依赖它的断言集合的映射，用于选一批有意义的测试，不是覆盖率保证。"),
    "按依赖取并集，加关键烟测；未知影响退回全量", "只跑文件名与改动文件最像的一条",
    ["给每个用例标出保护的业务路径。","为改动域追查直接及传递依赖。","合并受影响用例并必跑关键烟测。","遇到未知边界扩大范围，并定期全跑来校准映射。"],
    "能用测试数量判断这次改动已经被覆盖吗？",
    [("选的是风险覆盖，不是方便覆盖","成本大时实际有两套运行策略：拉取请求执行影响集，固定周期运行全量以校准漏选。用例分类可以对应关键路径、触发域和副作用，而非只对应代码目录。"),
     ("看传递依赖","示例中金额计算被确认流程依赖，改金额会选上确认用例；使用可终止的 visited 集处理循环。必须从会被改动影响的组件向消费方走，不能把边的方向写反。"),
     ("保守处理不确定性","公共组件新加且还没有映射时，退回全量。代码覆盖率只说明某行执行过，无法证明必需断言被验证。要增加缺陷注入或突变测试找观察点的弱项。")],
    '''risk = {
    "money": {"confirm"},
    "confirm": {"receipt"},
    "availability": set(),
    "receipt": set(),
}
cases = {
    "money": {"rounding"}, "confirm": {"blocked-price"},
    "availability": {"full-slot"}, "receipt": {"receipt-amount"},
}
smoke = {"create-booking"}
all_cases = set().union(smoke, *cases.values())

def select(changed):
    if not set(changed) <= risk.keys():
        return all_cases.copy()
    pending, seen = list(changed), set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        pending.extend(risk[name])
    return set().union(smoke, *(cases[name] for name in seen))

assert select(["money"]) == smoke | {"rounding", "blocked-price", "receipt-amount"}
assert select(["unknown"]) == all_cases
assert select([]) == smoke
''',
    [("漏传递影响","去掉 confirm 到 receipt 这条边。","跨组件回归用例漏选；选择器测试必须对实际错误响铃。"),("新模块没分类","传入 unknown。","退回全量，不默许只跑烟测。")],
    ["直接和传递用例都纳入。","相同用例不会重复运行。","空变更仍运行烟测。","未知变化触发预先约定的全量策略。"],
    "全量是安全网，选择器是提速工具。映射捕捉的是风险，而不是行数。")

add("flaky-tests", "偶发失败：用证据决定修测试还是修产品", 22,
    "保留首次结果，区分偶发、稳定回归和环境中断。",
    "一条预约测试跑五次结果红绿交替；团队之前总在重跑变绿后直接放行。",
    ("偶发失败", "在版本和已知输入一致时，同一断言有时通过，有时失败。不要还没核对运行条件就先贴上这个标签。"),
    "锁定版本和输入、保留首次结果与每次证据，再分类排查", "只记录最后一次绿色结果",
    ["冻结代码版本、数据与已知环境条件。","在有限次数内复跑并记录每次分类。","用第一次失败证据检查异步时序和隔离。","隔离仅降噪，给负责人和退出标准。"],
    "失败用例重跑变绿，就能说本次没有回归吗？",
    [("重跑不能覆盖原始事实","保存第一次与后续尝试；同一用例同版本只在指定条件下比较。稳定失败是明确的回归候选，红绿交替才提示时序、共享状态或真实竞争。"),
     ("环境错误有自己的一类","环境中断可能导致有效样本不足，不能把它混进通过率，也不能计作断言失败。若有效断言相互矛盾但出现环境噪声，可以同时标记 flaky 和环境告警；这里分类为主因。"),
     ("隔离应短时且有出口","隔离记录负责人、复现步骤、截止日期和解除阈值。真实处理要看失败前的状态快照，优先用条件等待代替固定 sleep，或消除复用数据带来的污染。")],
    '''def classify(attempts):
    valid = [case for case in attempts if case != "infra_error"]
    if not valid:
        return "no_evidence"
    if len(set(valid)) > 1:
        return "flaky"
    if "infra_error" in attempts:
        return "incomplete"
    return "stable_" + valid[0]

def report(attempts):
    return {
        "first": attempts[0] if attempts else "missing",
        "category": classify(attempts),
        "all_attempts": tuple(attempts),
    }

result = report(["fail", "pass", "pass"])
assert result["first"] == "fail" and result["category"] == "flaky"
assert report(["fail", "fail"])["category"] == "stable_fail"
assert report(["infra_error", "pass"])["category"] == "incomplete"
assert report(["infra_error"])["category"] == "no_evidence"
''',
    [("绿色覆盖首次失败","输入 fail、pass、pass。","保留 first=fail，分类 flaky。"),("执行器连续故障","没有任何业务断言完成。","标为无有效证据，不算已通过。")],
    ["首次与每次尝试都可追溯。","单次环境故障不会冒充产品回归。","稳定失败保留阻断策略。","隔离有明确恢复标准。"],
    "可疑的通过也要有证据。不要让最后一次跑绿替代对首次失败原因的排查。")

add("dataset-versioning", "评测数据集：版本、切分与泄漏检查", 26,
    "构建不可混淆的训练、开发和盲测样本集。",
    "同一预约规则有几个改写版本。如果把改写随机分到不同集合，开发阶段会提前看见盲测内容。",
    ("按组切分", "把同一来源及其改写看作一个组，在组层面分配到集合，而不是对每行独立随机分配。"),
    "相同来源放同一集合，并锁定数据和规则版本", "只比较文本是否逐字相同",
    ["给样本分配固定 ID 与来源组。","对整个来源组做开发与留出切分。","为规范化内容生成清单指纹并保存。","比较两次结果前同时检查样本、评分规则与切分。"],
    "相同规则的改写文本不完全一样，可以分到开发和盲测两边吗？",
    [("先定义来源组","完全相同的文本去重还不够：同一个工单的对话变体、同一预约约束的改写都可能泄漏。示例要求同一 group 只能有一个 split；组的由来要能解释，真实数据还需近似重复检查。"),
     ("规范化指纹是复核入口","排序按样本 ID，序列化稳定后再做哈希。调整行顺序不改变标识；改预期、规则来源或 split 会改变。在报告中再保存评分规范标识、运行配置和评估集用途，指纹本身不保证标签正确。"),
     ("盲测结果只用于少数决策","开发可以看开发子集的逐项错误；留出用作阶段性复核，不要边试提示词边逐题看盲测分。如果频繁查看留出分，逐渐会把它优化成开发集，应另建新的独立留出。")],
    '''from hashlib import sha256
import json

def fingerprint(samples):
    ids, split_by_group = set(), {}
    for sample in samples:
        key, group, split = (sample["id"], sample["group"], sample["split"])
        if key in ids:
            raise ValueError("duplicate sample ID")
        if split not in {"train", "dev", "holdout"}:
            raise ValueError("unknown split")
        if split_by_group.setdefault(group, split) != split:
            raise ValueError("group leakage")
        ids.add(key)
    data = sorted(samples, key=lambda row: row["id"])
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()

rows = [
    {"id": "q1", "group": "queue", "split": "dev", "expect": "wait"},
    {"id": "q2", "group": "queue", "split": "dev", "expect": "wait"},
    {"id": "s1", "group": "slot", "split": "holdout", "expect": "read"},
]
assert fingerprint(rows) == fingerprint(list(reversed(rows)))
assert fingerprint(rows) != fingerprint([*rows[:2], {**rows[2], "expect": "deny"}])
''',
    [("变体跨切分","把 q2 调到 holdout。","同源组跨集合被拒绝。"),("重复编号","追加另一条 id=q1 的记录。","拒绝数据，不让结果字典悄悄覆盖。")],
    ["同组不跨集合。","只重排记录不会改变指纹。","修改预期会改变指纹。","用不同数据或不同规则的成绩不得直接归因模型。"],
    "数据集版本要能证明究竟评了什么，切分要保护你还没看过的检验题。")

add("rubrics", "评分标准与人工校准：从主观意见变成可复核证据", 26,
    "把清晰、正确与关键风险拆成维度，通过双人盲评调整标准。",
    "两位评审都说「有点不清楚」，但一人只有格式意见，另一人发现答复根本没有给出需要确认的下一步。",
    ("评分锚点", "用具体正反例说明某一档分数对应的可观察行为，让两个评审知道在对齐什么。"),
    "单独写清维度和正反例，独立打分后复核分歧", "取两个总体满意度的均值，不问证据",
    ["把正确性和行动可读性拆开。","写档位锚点和可引用证据。","两人独立评分，保留原值和分歧项。","通过讨论更新标准版本，再做一次新的校准。"],
    "两个评审对是否可操作意见相反，只看总体平均分可以吗？",
    [("定义可观察档位","对 CaseLab 的确认回答，正确性要判断有无声称已预约，可操作性要判断用户是否知道确认哪个槽位。每项有 0、1、2 三个档位，新样本由两个评审各自看文本和同一证据。"),
     ("盲评后追问同一条证据","示例按样本与维度列出分歧，绝不平均成一个值。U1 的行动指示可看具体呈现；先复核是不是标准模糊，还是某位评审遗漏证据，再记录裁决；原始标注保留。"),
     ("简单一致率不是质量证明","两个评审可能一致地理解错规则，稀有高风险类别也会被大量一致的简单样本淹没。把关键项单独抽样，标准改动单独发版本；高影响分歧需要仲裁后再进入金标集。")],
    '''DIMENSIONS = ("correctness", "next_step")
left = {
    "u1": {"correctness": 2, "next_step": 1},
    "u2": {"correctness": 0, "next_step": 0},
}
right = {
    "u1": {"correctness": 2, "next_step": 2},
    "u2": {"correctness": 0, "next_step": 0},
}

def calibrate(a, b):
    if set(a) != set(b):
        raise ValueError("reviewers must score the same samples")
    disagreements = []
    for sample in sorted(a):
        for dim in DIMENSIONS:
            x, y = a[sample][dim], b[sample][dim]
            if x not in {0, 1, 2} or y not in {0, 1, 2}:
                raise ValueError("unknown score")
            if x != y:
                disagreements.append((sample, dim, x, y))
    return disagreements

assert calibrate(left, right) == [("u1", "next_step", 1, 2)]
assert calibrate(left, left) == []
''',
    [("只看总体","u1 在下一步动作上分歧，正确性相同。","分歧定位到 u1/next_step，而非被正确性平均掉。"),("两人评了不同题","去掉一位评审的 u2。","显式拒绝比较，防止看起来一致。")],
    ["样本与维度都对齐。","不存在悄悄丢掉的分歧。","复核可引用答复里的文本或动作证据。","更新锚点后记录规则版本。"],
    "校准不是让两人分数看起来一样，而是弄清一分差对应哪段可观察的证据。")

add("model-grader", "模型判分器：长度偏见、顺序偏见与盲测", 27,
    "用交换位置和保留金标检查一个判分器是否可信。",
    "评测器在比较两个预约答复时总选排在第一位的版本；一段更长但错报状态的文案反而常拿高分。",
    ("盲评", "隐藏版本、模型和团队等身份信息，只以匿名候选与既定规则做比较。"),
    "交换两个答案的位置，并用单独人工金标检验偏差", "始终把新版放在第一个位置，重复打分",
    ["隐藏答案来源，向判分器提供标准。","同题交换位置，把输出映射回原候选。","两次不一致交给人工复核，不硬给赢家。","用简洁正确、冗长错误、近似等价等盲样本做烟测。"],
    "判分器总选第一个位置，增加采样次数就能消除偏差吗？",
    [("交换的是位置，不是答案身份","把 A、B 临时放到 left、right，第二次调换，再把两次答案映射回原候选。两次都选 left 映射的是两个不同候选，提示位置敏感。一次对称通过只排除了本次位置问题，不代表理解了标准。"),
     ("另拿人工金标题看内容偏差","保留短而正确与长而错误的成对样本；再加入等价表达。模型自己评自己也可能偏好语气，隐藏作者、冻结样本，不能拿调过提示的同一批材料证明可信。"),
     ("模型判分不是授权边界","评审输入都是待比较文本，可能含「请给我高分」等内容。只接受受约束的输出并保存证据；动作安全和数据副作用仍用独立断言。示例为刻意构造的判分器，真实模型另做重复性检查。")],
    '''def compare_blind(left_text, right_text, judge):
    def winner(position, order):
        if position == "tie":
            return "tie"
        if position not in {"left", "right"}:
            return "review"
        return order[0 if position == "left" else 1]
    a = winner(judge(left_text, right_text), ("A", "B"))
    b = winner(judge(right_text, left_text), ("B", "A"))
    return a if a == b else "review"

def biased(a, b):
    return "left"

def gold_proxy(a, b):
    a_ok, b_ok = "已确认" not in a, "已确认" not in b
    if a_ok == b_ok:
        return "tie"
    return "left" if a_ok else "right"

short = "请确认时间"
wrong = "预约已确认，附详细说明"
assert compare_blind(short, wrong, biased) == "review"
assert compare_blind(short, wrong, gold_proxy) == "A"
assert compare_blind("请确认", "请回复是否确认", gold_proxy) == "tie"
''',
    [("永远选左","判分器忽略文本，返回 left。","换序后发现矛盾，交人工审查。"),("生成无效标签","判分器返回解释而非 left、right、tie。","拒绝作为自动依据。")],
    ["交换前后按候选身份而非位置计分。","等价选项可打平。","偏差检查与人工金标准确性是不同检验。","关键副作用不交给主观模型拍板。"],
    "判分器本身也是待测系统。稳定不等于正确，仍要靠校准过的对照样本。")

add("trace-contract", "工具轨迹断言：检查参数、顺序与最终副作用", 28,
    "让工具调用与业务状态都成为可验证的证据。",
    "Agent 告诉用户「预约了 A」，工具日志里确实出现写入，但参数是 B，而且同一写调用发生了两次。",
    ("轨迹契约", "事前约定本场景可以发生哪些动作、携带什么参数、出现什么顺序以及应留下什么状态。"),
    "同时看正确确认、写入参数、重试行为与最终状态", "只要工具名在轨迹里出现一次就判通过",
    ["捕捉确认、工具调用与响应序列。","用状态机检查确认在前、写入在后，并匹配槽位。","从独立存储读最终状态与条数。","保留首次越界的事件号和前后状态差。"],
    "回复说对、工具名也对，为什么还能判失败？",
    [("事件里记录最小必要字段","对教学预约，记录动作类型与合成槽位就够用。顺序来自同一运行的可信有序记录；真实分布式追踪若顺序不确定，应记录因果关系和缺失状态，不能只按未同步时钟硬排。"),
     ("正确顺序不等于正确载荷","示例要求确认 A 且接下来写 A，错槽位无法通过。同类型动作重复也会失败。真实系统中相同幂等键的网络重试可能允许，轨迹契约应区分一次业务操作与多次传输。"),
     ("状态从另一处读","工具说写入成功不等于确实保存，也不保证只保存一次。单独观察持久状态最可靠；例子把最终行列表作为独立输入，要求新出现的预约恰好是预期一条。")],
    '''def check(events, final_rows, expected):
    confirmed, writes = False, 0
    for index, (kind, slot) in enumerate(events):
        if kind == "confirm":
            confirmed = slot == expected
        elif kind == "save":
            writes += 1
            if not confirmed or slot != expected or writes > 1:
                return ("invalid_write", index)
        elif kind != "check":
            return ("unknown_action", index)
    if writes != 1:
        return ("missing_write", None)
    if final_rows != [expected]:
        return ("unexpected_state", None)
    return ("ok", None)

normal = [("check", "A"), ("confirm", "A"), ("save", "A")]
assert check(normal, ["A"], "A") == ("ok", None)
assert check(normal[:2] + [("save", "B")], ["B"], "A") == ("invalid_write", 2)
assert check(normal + [("save", "A")], ["A", "A"], "A") == ("invalid_write", 3)
assert check(normal, [], "A") == ("unexpected_state", None)
''',
    [("写错槽位","确认 A 后提交 save B。","报告定位触发点，不把工具名正确算作通过。"),("虚假成功","工具报告写成功但状态读不到结果。","错误归类为状态不符，不只归给文案。")],
    ["未确认就写被拦。","确认与写入的槽位相同。","重复写入检测。","工具回显和持久状态分别核对。"],
    "给每一段证据一个独立观察点。名字、参数、顺序和结果必须分别检查。")

add("gate-statistics", "发布门槛：硬失败、样本量和统计不确定性", 29,
    "把严重规则违规、样本不足和一般质量下降分成不同发布结果。",
    "两次评测都零失败：一次跑了 5 个样本，另一次跑了 100 个。两者的保证一样强吗？",
    ("置信区间", "在抽样模型成立时，用数据给未知比例提供一个带不确定性的范围，而不是把观察比例当真值。"),
    "越权直接阻断，其他指标同时看样本量和不确定性", "通过率是 100% 就可以发布",
    ["先沿关键风险检查禁止事件与缺失证据。","给一般质量声明约定通过率与最小样本数。","计算 Wilson 下界，判断证据是否足够。","单独报告每个关键分层，比较版本时按同一批样本做配对。"],
    "5/5 和 100/100 都通过，为什么不应该一视同仁？",
    [("发布有硬门槛和证据门槛","越权写入是硬失败，一次也阻断；大样本均分抵消不了。普通用例可以看通过率的 Wilson 区间。在相同样本上比较候选与基线时宜看配对差异而不是把两个比例当作独立。"),
     ("解释下界的条件","示例用 z=1.96 计算近似双侧 95% Wilson 区间下界。独立样本且分布具代表性才适用；同源样本和重复运行会扩大不确定性，不可重复计入样本量来缩小区间。"),
     ("状态要允许‘证据不够’","如果没有发现硬违规，但没有达到最小样本量或区间下界目标，进入复核而不是自动发布。对罕见但严重的风险要做定向测试，采样没发现不代表它为零。")],
    '''from math import sqrt

def lower_bound(passed, total, z=1.96):
    if not 0 <= passed <= total or total <= 0:
        raise ValueError("invalid counts")
    rate = passed / total
    center = rate + z*z / (2*total)
    radius = z * sqrt(rate*(1-rate)/total + z*z/(4*total*total))
    return (center - radius) / (1 + z*z/total)

def gate(passed, total, hard_fail, evidence_missing):
    if hard_fail:
        return "blocked"
    if evidence_missing or total < 30:
        return "review"
    if lower_bound(passed, total) < 0.90:
        return "review"
    return "pass"

assert lower_bound(5, 5) < lower_bound(100, 100)
assert gate(5, 5, False, False) == "review"
assert gate(100, 100, False, False) == "pass"
assert gate(100, 100, True, False) == "blocked"
assert gate(100, 100, False, True) == "review"
''',
    [("样本数不足","5 条全部通过，关键项均有证据。","复核，不把小样本 100% 当成强保证。"),("关键轨迹缺证据","普通准确率正常，但一条关键用例无轨迹。","复核或按产品策略阻断；不能算安全通过。")],
    ["硬失败优先于统计量。","无样本不能算 100%。","相关变体不会人造放大有效样本量。","报告样本量、区间条件和欠覆盖分层。"],
    "高置信不是高分的同义词。放行决策要说清楚样本来源、结果与剩余不确定性。")

add("evidence-report", "回归报告：把失败链接到可复跑证据", 24,
    "将前后对照变成可以分诊和重跑的动态清单。",
    "日报显示 95% 通过，但评审不知道是哪几项退化，是否应该联系执行器负责人。",
    ("证据引用", "把报告中的结论绑定到运行、样本、尝试及规则版本，别人可以沿同一入口复核。"),
    "保持失败与缺项显式，并附可复核的结果定位", "只给整体比例，不保存失败样本",
    ["确认两次结果使用同数据集和规则。","按样本合并回报，分类退化、恢复、无证据。","将严重、环境和普通变化保留不同处置。","报告保存定位标识，并为复跑创建新尝试。"],
    "候选报告少了一条结果，该算成功、失败还是缺证据？",
    [("用全并集找缺行","直接内连接会把只在一边的样本悄悄删除。用全并集构造摘要；正式场景最好再与声明的样本集合对比，以发现两次都缺失的样本。"),
     ("结果按语义分类","示例中 pass 到 fail 表示退化；没有记录或只看到执行器错误是需要补证据，不是模型退化。新旧测试标准变化时不自动做归因。"),
     ("保留能复跑的定位信息","运行编号和样本编号应能定位对应输入、版本和真实结果，避免把用户输入全文放进公开报告。复跑另生成尝试标识；失败前后的信息都留下。")],
    '''def summarize(dataset, rules, base, candidate):
    if base["dataset"] != dataset or candidate["dataset"] != dataset:
        raise ValueError("inconsistent dataset")
    if base["rules"] != rules or candidate["rules"] != rules:
        raise ValueError("inconsistent rules")
    old, new = base["results"], candidate["results"]
    rows = {}
    for case in sorted(old.keys() | new.keys()):
        a, b = old.get(case), new.get(case)
        if a in {None, "infra"} or b in {None, "infra"}:
            change = "needs_evidence"
        elif a == "pass" and b == "fail":
            change = "regression"
        elif a == "fail" and b == "pass":
            change = "fixed"
        else:
            change = "unchanged"
        rows[case] = (change, base["run"], candidate["run"])
    return rows

first = {"dataset": "d1", "rules": "r2", "run": "demo-1",
         "results": {"ask": "pass", "repeat": "pass"}}
second = {**first, "run": "demo-2", "results": {"ask": "fail"}}
rows = summarize("d1", "r2", first, second)
assert rows["ask"] == ("regression", "demo-1", "demo-2")
assert rows["repeat"][0] == "needs_evidence"
''',
    [("候选漏回报","候选没返回 repeat。","显示缺证据；保留两个运行引用。"),("规则不一致","候选改用 r3，看起来分更高。","拒绝直接对比并说明版本差异。")],
    ["样本缺行不被内连接丢掉。","退化能精确到样本和两个运行。","执行故障不被算作模型错误。","报告包含复跑输入与规则定位。"],
    "好报告不是发一个分数，而是让下一位读者知道先看哪条证据、怎样验证。")

add("graduation", "毕业项目：预约候选发布与故障演练", 40,
    "将数据检查、规则判定、重放和报告合成可交付的一次演练。",
    "团队要把预约助手从只读扩展为确认后可写。你需要用新旧版本对照，覆盖误写、缺记录和重试。",
    ("最小验收集", "覆盖必须保护的关键路径和高影响失败的有限集合，用来交付可复跑的首轮质量证据。"),
    "锁定数据集，强制记录副作用，并将故障输入和处置绑定到同一运行", "只录一个正常流程视频后宣称发布没问题",
    ["设计只读、等待确认、确认成功、写入回执丢失与缺轨迹五种样本。","分别运行基线、候选，收集答复、轨迹与独立状态。","验证每个问题被正确分类；报告能够指向样本。","修复后重跑原样本；状态允许缺证据复核。"],
    "怎样让评审独立验证这次修复，而不需要相信我们的口头说明？",
    [("把前几课的约束放在一个用例里","定义输入与状态期望，执行端独立采集动作和存储行数。确认后写入回执丢失时，可能看到两次发送但最终只一行：说明重试不是第二次逻辑操作。没有轨迹则不能证明没多写。"),
     ("最小项目能复跑，不只演示","下面把五个样本的观察值写成固定输入来验证发布脚本；这是报告层的工作示例。真实交付另外接一个本地保存适配器与假时钟，跑真实领取、恢复、重试，直接采集这几条观察。"),
     ("交付物的几个边界","给评审一条命令、样本清单、基线和候选版本、故障开关、预期报告，并注明缺证据、拦截和放行各自含义。修复后新建候选记录复跑；不能覆盖最初的失败报告。")],
    '''EXPECT = {
    "read": ("show", 0, 0),
    "ask": ("confirm", 0, 0),
    "approved": ("done", 1, 1),
    "lost_reply": ("done", 2, 1),
    "trace_required": ("confirm", 0, 0),
}

def review(observed):
    rows = {}
    for name, expected in EXPECT.items():
        actual = observed.get(name)
        if actual is None or actual[1] is None or actual[2] is None:
            rows[name] = "needs_evidence"
        elif actual != expected:
            rows[name] = "blocked"
        else:
            rows[name] = "pass"
    release = ("blocked" if "blocked" in rows.values() else
               "review" if "needs_evidence" in rows.values() else "pass")
    return release, rows

baseline = dict(EXPECT)
candidate = {**baseline, "ask": ("confirm", 1, 1),
             "trace_required": ("confirm", None, 0)}
release, report = review(candidate)
assert release == "blocked" and report["ask"] == "blocked"
assert report["trace_required"] == "needs_evidence"
assert report["lost_reply"] == "pass"
assert review({**baseline, "trace_required": None})[0] == "review"
assert review(baseline)[0] == "pass"
''',
    [("正在确认却写了一次","候选在 ask 场景报告实际写入一行。","定位 ask，明确阻断。"),("补了一条正确动作却漏采轨迹","撤掉 trace_required 的轨迹证据。","结果仍需复核，不能宣布修复。"),("丢回执后的错误重试","把 lost_reply 最终记录数改为 2。","请求重试次数正确仍然阻断，查幂等边界。")],
    ["可以复跑最小样本和故障变体。","真实副作用行数独立检查。","操作违规高于其他绿灯。","修复前后按同一数据集和规则比较并保留两份报告。"],
    "毕业验收是可复跑、有信号、有边界的证据，不是任选一套框架或展示一次绿灯。")
