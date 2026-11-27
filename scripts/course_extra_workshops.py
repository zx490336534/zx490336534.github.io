"""Further runnable workshops using synthetic project data."""

ROOM_WORKSHOPS = {
    "ui-state": (
        ("ui-state", "页面状态：别让加载、空结果与失败互相冒充", 12,
         "区分首次加载、刷新旧结果、成功但为空，以及失败后的重试入口。",
         "RoomLab 第一次打开还没有布局；后来用户刷新的是已经存在的布局。两次请求都可能失败，但第一次需要一个明确的恢复入口，第二次则应该保留当前场景。",
         ["把请求状态和当前可用布局分别存储。", "先判断是否有已确认结果，再决定失败后画哪一种界面。", "只有当前请求成功才替换页面数据，迟到的请求不能盖过它。"],
         '{"phase":"error","lastGood":{"revision":4,"items":[]}}',
         "按首次进入、首次失败、刷新失败、成功但为空四种状态，给两种视图各写一个可观察断言。",
         "刷新已有布局失败时，应该清空界面让用户重新开始吗？",
         ["保留已确认布局，说明刷新失败并提供重试", "清空界面并显示没有布局"], 0,
         "请求失败只说明没有拿到新结果。已确认的上个结果仍然可以展示。"),
        ("派生界面", "用已知状态决定界面显示什么，不让各组件自己猜测加载或失败。"),
        ("同样是请求失败，为什么首页和已有布局的页面应该表现不同？",
         ["入口接收请求标识和当前 UI 状态。", "提交后进入加载，并保留 lastGood。", "只让同一个请求的结果更新状态。", "渲染函数根据阶段和已知布局选择初始提示、空状态、故障提示或画布。"],
         [("让失败和空状态彻底分开", "空意味着成功得到一份空结果；失败意味着不知道新结果。代码让它们走不同分支，界面不再用同一个布尔值概括整个状态。"),
          ("用中央派生函数避免双视图互相打架", "describe 只读取状态，无副作用；二维与三维都使用同一份数据。一般可以从这里再派生按钮文字和 aria-live 的短状态，而不是在两个组件里各自维护请求阶段。"),
          ("用请求标识守住竞态边界", "快速连续点击时只接收当前请求。旧结果被丢弃时返回原状态对象，让调用者可以判断是否需要更新，避免把晚到的成功覆盖更新的失败或合法空结果。")],
         "javascript",
         """const assert = require('node:assert/strict');
const idle = { id: 0, phase: 'idle', lastGood: null };

function start(s) {
  return { ...s, id: s.id + 1, phase: 'loading' };
}

function finish(s, id, result) {
  if (id !== s.id || s.phase !== 'loading') return s;
  if (!result.ok) return { ...s, phase: 'error' };
  return { ...s, phase: 'success', lastGood: result.layout };
}

function describe(s) {
  if (s.phase === 'error') return s.lastGood ? '旧布局 + 重试' : '错误 + 重试';
  if (s.phase === 'loading') return s.lastGood ? '旧布局 + 刷新中' : '首次加载中';
  if (s.phase === 'success') return s.lastGood.items.length ? '画布' : '布局为空';
  return '开始生成';
}

const first = start(idle);
assert.equal(describe(finish(first, first.id, { ok: false })), '错误 + 重试');
const empty = { ok: true, layout: { revision: 4, items: [] } };
const success = finish(first, first.id, empty);
assert.equal(describe(success), '布局为空');
const refresh = start(success);
assert.equal(describe(refresh), '旧布局 + 刷新中');
assert.equal(describe(finish(refresh, refresh.id, { ok: false })), '旧布局 + 重试');
assert.equal(finish(refresh, first.id, empty), refresh);""",
         [("失败时误显示为空", "在首次加载和刷新时各注入一次失败。", "前者给恢复入口，后者保留已知布局；两者都不等于成功为空。"),
          ("旧请求掩盖新请求", "刷新中重新发起一次请求，再回传第一次的完成事件。", "当前请求和界面保持不变。"),
          ("组件各自保留过期副本", "让二维图和三维预览都读取同一快照，再把阶段切成刷新失败。", "两侧显示同一版本；提示文字从共享阶段生成。")],
         ["首次失败和成功为空有不同的可见文案。", "刷新失败不清除 lastGood。", "旧请求晚到不能改 id、phase 或当前布局。"],
         "把请求阶段和有效数据分开建模，故障提示才能与画布并存。"),
    ),
    "retrieval-grounding": (
        ("retrieval-grounding", "检索增强：让布局建议有证据可核对", 12,
         "让模型引用真正用到的约束，并对过期或不相干的规则选择不下结论。",
         "RoomLab 要给小会议室选择桌子。检索结果有不同房型的规则，还混着一份已经被替换的说明。一条相似文本不等于可以直接用于当前项目。",
         ["按房型和生效版本过滤，再把有限的相关条目交给模型。", "模型输出建议和值以及证据编号，不直接返回已批准状态。", "提交前核对编号、值和当前规则版本；证据不足就暂缓结论。"],
         '{"roomType":"meeting","revision":3,"evidence":["rule-clearance"]}',
         "故意在样本里插入旧版约束、另一房型约束和不存在的引用编号，记录每种为何不应通过。",
         "模型引用了一条确实存在、但已经失效的规则，可以照样提交吗？",
         ["不用，只要编号存在就算有来源", "不能，要核对这条规则是否对当前任务有效"], 1,
         "引用编号只能证明条目存在，不能证明它适用、当前有效或支持结论。"),
        ("证据约束", "建议的值必须能由本次检索范围内的有效条目支撑。"),
        ("模型答得很像真的，也附了规则编号。怎么知道它真的用了这份规则？",
         ["先用结构化条件过滤房型和版本。", "对候选词作简单匹配，少量返回并保留来源编号。", "读模型给出的建议及引用，判断引用是否来自本次候选。", "核对规则值是否支持建议，无法证明时要求更多信息。"],
         [("先过滤，后排序", "本例按房型与当前版本硬过滤，再做关键字匹配。真实检索可以用检索器得分排顺序，但分数不应跨越适用范围；旧规则更像用户问法也不能拿来批准方案。"),
          ("命中引用不等于支持结论", "验证先确认来源在当前候选列表，再比较其确定性值。这里用可直接比较的宽度作为示例。开放式文本建议需要额外的人审、更细的事实检查或明确回退。"),
          ("缺失证据的结果要有清楚状态", "need-evidence 和 value-mismatch 区分没找到依据与有依据却支持不了这个值。业务层可给不同提示，但两种都不应自动发布建议。")],
         "python",
         """RULES = (
    {'id': 'old', 'kind': 'meeting', 'rev': 2, 'tag': 'desk', 'width': 90},
    {'id': 'other', 'kind': 'storage', 'rev': 3, 'tag': 'desk', 'width': 130},
    {'id': 'rule-clearance', 'kind': 'meeting', 'rev': 3, 'tag': 'desk', 'width': 110},
)

def retrieve(kind, rev, tag):
    return [r for r in RULES if (r['kind'], r['rev'], r['tag']) == (kind, rev, tag)]

def audit(candidate, evidence):
    sources = {r['id']: r for r in evidence}
    rule = sources.get(candidate.get('evidence'))
    if rule is None:
        return 'need-evidence'
    if candidate.get('width') != rule['width']:
        return 'value-mismatch'
    return 'supported'

evidence = retrieve('meeting', 3, 'desk')
assert [r['id'] for r in evidence] == ['rule-clearance']
assert audit({'evidence': 'old', 'width': 90}, evidence) == 'need-evidence'
assert audit({'evidence': 'other', 'width': 130}, evidence) == 'need-evidence'
assert audit({'evidence': 'rule-clearance', 'width': 100}, evidence) == 'value-mismatch'
assert audit({'evidence': 'rule-clearance', 'width': 110}, evidence) == 'supported'
assert audit({'evidence': 'rule-clearance', 'width': 110}, []) == 'need-evidence'""",
         [("跨房型引用", "把储物间规则的编号写进会议室建议。", "引用不在当前候选集中，结果为 need-evidence。"),
          ("正确引用、错误结论", "保留正确规则编号，但把建议宽度改成另一个数字。", "结果为 value-mismatch，不自动提交。"),
          ("没有可用资料", "让检索列表为空。", "报告证据不足，而不是改变规则优先级凑一个结果。")],
         ["旧版本和另一房型的检索结果被剔除。", "错误数值即使有真实编号也不通过。", "只有当前范围内且能核对的结论被标为 supported。"],
         "检索提供候选；应用要核对范围、有效期和证据能否支持结论。"),
    ),
}

CASE_WORKSHOPS = {
    "test-boundaries": (
        ("test-boundaries", "边界值与不变量：从几个例子扩展到一类输入", 11,
         "用明确的输入边界和业务不变量解释为什么增加某条用例。",
         "CaseLab 要验证每个团队最多能预约几次。两个常规输入跑通不能说明边界正确，也不能说明排序变化时结果一致。",
         ["从规则提取最小值、最大值和两侧一格。", "写出跨多组数据都应该成立的关系，例如调换无关记录顺序不该改变数量。", "用循环枚举小范围输入，失败时报告实际输入而不只告诉你断言失败。"],
         "capacity = 3\nassert ok(2) and ok(3) and not ok(4)",
         "把示例里的 <= 改成 <，确认哪条断言报错；再补一个独立检查，防止负数被接受。",
         "测试预约上限为 3，最值得先覆盖哪一组？", ["2、3、4，另外检查无效的负数", "只测 1、2 和 100"], 0,
         "边界两侧能揭露开闭区间写反，负数则检查输入校验。"),
        ("不变量", "一类输入变化前后必须保持的行为，例如改变记录顺序不能改变计数。"),
        ("样例全过了，怎么找到写错一个比较符号或重复计数这类问题？",
         ["写下预约数量的类型与区间。", "枚举上限附近的合法和非法输入。", "复制并重排记录，核对数量一致性。", "对去重键重复的记录，验证统计幂等并记录反例。"],
         [("用边界对照比较符号", "accepts 同时检查类型和开闭区间。Python 中 bool 是 int 子类，这里用 type(value) is int，避免 True 被当成次数。写出输入约束比只给几个测试数字更有意义。"),
          ("用关系断言扩展用例，而不是复制同一个期望值", "换序与重复写入是一类变换。若业务按唯一预约编号计数，打乱顺序不能改变数量，重复发送同一批记录也不能让数量翻倍。"),
          ("用最小反例定位出错规则", "带着输入值写断言信息；当一批断言失败时，先用最小的失败值单跑。真实生成式测试可扩展范围并收缩反例；这里的确定性枚举用于先建立判断。")],
         "python",
         """from itertools import permutations

def accepts(value, limit):
    return type(value) is int and 0 <= value <= limit

def booked_count(rows):
    return len({row['id'] for row in rows if row['status'] == 'confirmed'})

for limit in range(1, 6):
    pairs = [(0, True), (limit - 1, True), (limit, True), (limit + 1, False), (-1, False)]
    for value, expected in pairs:
        assert accepts(value, limit) == expected, (value, limit)
assert not accepts(True, 3)

base = [
    {'id': 'a', 'status': 'confirmed'},
    {'id': 'b', 'status': 'cancelled'},
    {'id': 'c', 'status': 'confirmed'},
]
assert booked_count(base) == 2
for shuffled in permutations(base):
    assert booked_count(shuffled) == booked_count(base)
assert booked_count(base + base) == booked_count(base)
assert booked_count([base[1]]) == 0""",
         [("上限错误", "将 <= 改成 < 或把边界对比写反。", "上限那一个输入失败，明确指出受影响限制值。"),
          ("真假值混进整数", "把 True 作为预约数量传入。", "它返回 False，不被解释为 1。"),
          ("重复记录抬高统计", "把同一批、同一预约编号的记录重复输入。", "唯一有效预约的总数保持不变。")],
         ["闭区间端点可用，端点外不可用。", "类型错误与数值错误都能触发失败。", "换序和同编号重复写入不改变计数。"],
         "边界断言找比较符号错误，不变量断言找一整类数据变化下的错误。"),
    ),
    "parallel-fixtures": (
        ("parallel-fixtures", "并行用例的数据隔离：谁创建，谁清理", 12,
         "让同一条用例开多个执行器时，不争抢数据，也不清掉别人的结果。",
         "两条用例都要创建一个名为 review 的临时预约。串行时各自通过，跑到同一批次里却相互覆盖，一个执行器清理时还影响另一个。",
         ["给每次测试调用生成独立作用域，而不是拿用例名称做全局唯一键。", "在创建时保存真正拿到的资源标识。", "正常结束和断言异常都走清理；清理只能删除自己创建的标识。"],
         "namespace = (run_id, worker_id, case_attempt_id)",
         "写一个用例故意抛错，再和另一条模拟用例交错运行；检查出错后的清理没有破坏其他会话。",
         "测试失败后的清理该按什么删除数据？", ["删除全部名为 review 的记录", "按本次实际创建的资源标识，且限定本次作用域"], 1,
         "仅按显示名称会误删并发执行创建的同名资源。"),
        ("用例夹具", "测试开始时准备数据、结束后清理数据的一段可复用逻辑。"),
        ("串行回归都过了，一并行就偶尔找不到数据，应该先查哪里？",
         ["在每个执行尝试生成作用域，并在夹具中保存。", "写入时绑定资源和作用域，读取也使用同一组键。", "并行执行相同显示名的用例，验证彼此不可见或不互相覆盖。", "在异常路径同样释放本次资源，核对另一个用例的记录仍存在。"],
         [("名称和所有权分开", "名称为人服务，并不适合做清理条件。资源标识至少包含运行、执行器和尝试；演示以元组表示隔离。相同用例重试需要新尝试身份，避免旧清理动作影响新运行。"),
          ("清理绑定主流程退出", "contextmanager 的 finally 段即使断言失败也会执行。真实进程被杀时 finally 不保证运行，因此需要按创建范围、租约或过期策略定期对账，而非直接全库删同名记录。"),
          ("把隔离验证成契约", "用嵌套调用模拟两个生命周期交错：当 B 出错退出时 A 尚在运行。断言清理只影响 B；不必等待真实线程竞速，仍可稳定捕捉共享命名空间错误。")],
         "python",
         """from contextlib import contextmanager

rows = {}

@contextmanager
def booking(scope, display_name):
    resource = (*scope, display_name)
    if resource in rows:
        raise ValueError('fixture_collision')
    rows[resource] = {'status': 'reserved'}
    try:
        yield resource
    finally:
        rows.pop(resource, None)

with booking(('run-1', 'worker-A', 'attempt-1'), 'review') as a:
    try:
        with booking(('run-1', 'worker-B', 'attempt-1'), 'review') as b:
            assert a != b and len(rows) == 2
            raise RuntimeError('intentional test failure')
    except RuntimeError:
        assert a in rows and b not in rows
    with booking(('run-1', 'worker-B', 'attempt-2'), 'review') as retry:
        assert retry != b and a in rows
    assert a in rows
assert not rows""",
         [("多个用例放进同一个作用域", "把作用域简化为 display_name，把同名运行嵌套。", "第二个创建发生冲突；夹具应该隔离而不是覆盖。"),
          ("清理按名称", "在 B 退出时删除所有名为 review 的行。", "A 的记录应该仍在，断言会暴露越界清理。"),
          ("重试复用身份", "给第二次尝试继续使用 attempt-1。", "新旧操作无法区分；验收要求重试身份不同。")],
         ["同时运行的两条用例可以使用同一个显示名。", "抛错后及时清理本次资源，其他用例保持可运行。", "重试使用新身份；全部退出后没有临时记录。"],
         "先定义资源属于哪次执行，再让创建、读取、清理都遵守同一个范围。"),
    ),
}
