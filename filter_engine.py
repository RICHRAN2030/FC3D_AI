"""
过滤引擎 - 复刻3DBZ.exe的16种过滤方法
输入：全部1000注(000-999) + 过滤条件JSON
输出：过滤后的号码列表
"""
from itertools import product


def generate_all():
    """生成全部1000注"""
    return [(d1, d2, d3) for d1, d2, d3 in product(range(10), repeat=3)]


# ============================================================
# 16种过滤器 (与3DBZ.exe完全对应)
# ============================================================

def filter_sum(numbers, values):
    """和值过滤 - values: [10,11,12,13,14,15]"""
    if not values:
        return numbers
    vset = set(values)
    return [(a, b, c) for a, b, c in numbers if a + b + c in vset]


def filter_span(numbers, values):
    """跨度过滤 - values: [4,5,6,7,8]"""
    if not values:
        return numbers
    vset = set(values)
    return [(a, b, c) for a, b, c in numbers if max(a, b, c) - min(a, b, c) in vset]


def filter_ac(numbers, values):
    """AC值过滤 - values: [2,3]"""
    if not values:
        return numbers
    vset = set(values)
    def ac(a, b, c):
        return len({abs(a - b), abs(a - c), abs(b - c)})
    return [(a, b, c) for a, b, c in numbers if ac(a, b, c) in vset]


def filter_odd_even(numbers, ratios):
    """奇偶比过滤 - ratios: ["2:1", "1:2"]"""
    if not ratios:
        return numbers
    rset = set(ratios)
    def oe(a, b, c):
        odd = sum(1 for x in (a, b, c) if x % 2 == 1)
        return f"{odd}:{3 - odd}"
    return [(a, b, c) for a, b, c in numbers if oe(a, b, c) in rset]


def filter_big_small(numbers, ratios):
    """大小比过滤 - ratios: ["2:1", "1:2"]"""
    if not ratios:
        return numbers
    rset = set(ratios)
    def bs(a, b, c):
        big = sum(1 for x in (a, b, c) if x >= 5)
        return f"{big}:{3 - big}"
    return [(a, b, c) for a, b, c in numbers if bs(a, b, c) in rset]


def filter_012_road(numbers, roads):
    """012路过滤 - roads: ["201", "101", "120"]"""
    if not roads:
        return numbers
    rset = set(roads)
    return [(a, b, c) for a, b, c in numbers if f"{a % 3}{b % 3}{c % 3}" in rset]


def filter_group_type(numbers, types):
    """组选类型过滤 - types: ["组六", "组三", "豹子"]"""
    if not types:
        return numbers
    tset = set(types)
    def gt(a, b, c):
        s = len({a, b, c})
        if s == 3:
            return "组六"
        elif s == 2:
            return "组三"
        else:
            return "豹子"
    return [(a, b, c) for a, b, c in numbers if gt(a, b, c) in tset]


def filter_hundred(numbers, digits):
    """百位过滤 - digits: [0,1,3,8]"""
    if not digits:
        return numbers
    dset = set(digits)
    return [(a, b, c) for a, b, c in numbers if a in dset]


def filter_ten(numbers, digits):
    """十位过滤 - digits: [1,2,5,7]"""
    if not digits:
        return numbers
    dset = set(digits)
    return [(a, b, c) for a, b, c in numbers if b in dset]


def filter_unit(numbers, digits):
    """个位过滤 - digits: [0,3,7,9]"""
    if not digits:
        return numbers
    dset = set(digits)
    return [(a, b, c) for a, b, c in numbers if c in dset]


def filter_repeat_with_prev(numbers, prev_digits, repeat_counts):
    """重号过滤 - prev_digits: 上期号码[2,4,5], repeat_counts: [0,1,2]"""
    if not prev_digits or not repeat_counts:
        return numbers
    cset = set(repeat_counts)
    def count_repeat(a, b, c):
        curr = [a, b, c]
        prev = list(prev_digits)
        count = 0
        for x in curr:
            if x in prev:
                count += 1
                prev.remove(x)
        return count
    return [(a, b, c) for a, b, c in numbers if count_repeat(a, b, c) in cset]


def filter_sum_tail(numbers, tails):
    """和尾过滤(和值个位) - tails: [1,3,5,7]"""
    if not tails:
        return numbers
    tset = set(tails)
    return [(a, b, c) for a, b, c in numbers if (a + b + c) % 10 in tset]


def filter_prime_composite(numbers, ratios):
    """质合比过滤 - ratios: ["2:1", "1:2"]"""
    if not ratios:
        return numbers
    primes = {1, 2, 3, 5, 7}
    rset = set(ratios)
    def pc(a, b, c):
        p = sum(1 for x in (a, b, c) if x in primes)
        return f"{p}:{3 - p}"
    return [(a, b, c) for a, b, c in numbers if pc(a, b, c) in rset]


def filter_consecutive(numbers, counts):
    """连号过滤 - counts: [0,1] (连号对数)"""
    if not counts:
        return numbers
    cset = set(counts)
    def consec(a, b, c):
        nums = sorted([a, b, c])
        cnt = sum(1 for i in range(2) if nums[i + 1] - nums[i] == 1)
        return cnt
    return [(a, b, c) for a, b, c in numbers if consec(a, b, c) in cset]


def filter_head_tail_diff(numbers, values):
    """首尾差值过滤(百位-个位的绝对值) - values: [1,2,3,4,5]"""
    if not values:
        return numbers
    vset = set(values)
    return [(a, b, c) for a, b, c in numbers if abs(a - c) in vset]


def filter_exclude_numbers(numbers, exclude_list):
    """排除指定号码 - exclude_list: [(1,2,3), (4,5,6)]"""
    if not exclude_list:
        return numbers
    eset = set(exclude_list)
    return [(a, b, c) for a, b, c in numbers if (a, b, c) not in eset]


def filter_missing_total(numbers, ranges, missing_data=None):
    """遗漏总值过滤 - ranges: [[5,9],[10,14],[15,19],[20,24],[25,29],[30,34],[35,39]]
    missing_data: {"百位":{0:遗漏值,...}, "十位":{...}, "个位":{...}}
    遗漏总值 = 百位遗漏值 + 十位遗漏值 + 个位遗漏值
    """
    if not ranges or not missing_data:
        return numbers
    def in_ranges(val):
        for r in ranges:
            if r[0] <= val <= r[1]:
                return True
        return False
    h_miss = missing_data.get("百位", {})
    t_miss = missing_data.get("十位", {})
    u_miss = missing_data.get("个位", {})
    return [(a, b, c) for a, b, c in numbers
            if in_ranges(h_miss.get(a, 0) + t_miss.get(b, 0) + u_miss.get(c, 0))]


def filter_adjacent(numbers, adj_data):
    """相邻号码过滤 - adj_data: {"邻数集合": [1,3,5,6,8,9], "最少包含": [1,2,3]}
    要求组合中至少N个数字在相邻池中"""
    adj_set = set(adj_data.get("邻数集合", []))
    min_counts = set(adj_data.get("最少包含", []))
    if not adj_set or not min_counts:
        return numbers
    def count_adj(a, b, c):
        return sum(1 for x in {a, b, c} if x in adj_set)
    return [(a, b, c) for a, b, c in numbers if count_adj(a, b, c) in min_counts]


def filter_due_digits(numbers, due_data):
    """跳期过滤 - due_data: {"百位": [eligible], "十位": [...], "个位": [...]}
    只保留每位包含'该出'数字的组合"""
    h_set = set(due_data.get("百位", range(10)))
    t_set = set(due_data.get("十位", range(10)))
    u_set = set(due_data.get("个位", range(10)))
    return [(a, b, c) for a, b, c in numbers
            if a in h_set and b in t_set and c in u_set]


def filter_must_contain(numbers, must_digits):
    """必含号码(胆码) - must_digits: [8] 或 [8,7]"""
    if not must_digits:
        return numbers
    def contains_all(a, b, c):
        pool = [a, b, c]
        for d in must_digits:
            if d in pool:
                pool.remove(d)
            else:
                return False
        return True
    return [(a, b, c) for a, b, c in numbers if contains_all(a, b, c)]


# ============================================================
# 核心：应用过滤条件JSON
# ============================================================

FILTER_MAP = {
    "和值":       ("sum",           filter_sum),
    "跨度":       ("span",          filter_span),
    "AC值":       ("ac",            filter_ac),
    "奇偶比":     ("odd_even",      filter_odd_even),
    "大小比":     ("big_small",     filter_big_small),
    "012路":      ("road_012",      filter_012_road),
    "组选类型":   ("group_type",    filter_group_type),
    "百位":       ("hundred",       filter_hundred),
    "十位":       ("ten",           filter_ten),
    "个位":       ("unit",          filter_unit),
    "和尾":       ("sum_tail",      filter_sum_tail),
    "质合比":     ("prime_comp",    filter_prime_composite),
    "连号":       ("consecutive",   filter_consecutive),
    "首尾差":     ("head_tail",     filter_head_tail_diff),
    "必含号码":   ("must_contain",  filter_must_contain),
    "排除号码":   ("exclude",       filter_exclude_numbers),
    "跳期过滤":   ("due_digits",   filter_due_digits),
}


def apply_filters(conditions, prev_number=None, missing_data=None):
    """
    应用过滤条件，返回过滤后号码列表及过程日志
    missing_data: 遗漏值数据（用于遗漏总值过滤）
    """
    numbers = generate_all()
    log = []
    log.append(f"起始: {len(numbers)} 注")

    # 过滤顺序（含Howard策略）
    order = ["百位", "十位", "个位", "组选类型",
             "重号",          # 与上期重号
             "相邻号码",      # Howard: 上期±1号码
             "奇偶比",
             "大小比",
             "质合比",
             "AC值",
             "和值",
             "连号",
             "和尾",
             "遗漏总值",
             "跨度",
             "首尾差",
             "012路",
             "跳期过滤",      # Howard: 跳期分析(默认关闭)
             "必含号码", "排除号码"]

    for key in order:
        if key not in conditions:
            continue
        val = conditions[key]
        if not val:
            continue

        before = len(numbers)

        if key == "重号" and isinstance(val, dict):
            prev = val.get("上期号码", prev_number)
            counts = val.get("重号数", [0, 1, 2])
            if prev:
                numbers = filter_repeat_with_prev(numbers, prev, counts)
        elif key == "相邻号码" and isinstance(val, dict):
            numbers = filter_adjacent(numbers, val)
        elif key == "遗漏总值" and isinstance(val, list) and missing_data:
            numbers = filter_missing_total(numbers, val, missing_data)
        elif key in FILTER_MAP:
            _, func = FILTER_MAP[key]
            numbers = func(numbers, val)

        after = len(numbers)
        eliminated = before - after
        if eliminated > 0:
            log.append(f"  {key}: {val} → 淘汰{eliminated}注, 剩余{after}注")

    log.append(f"最终: {len(numbers)} 注")
    return numbers, log


def format_gl_output(numbers, issue="", seq=1):
    """格式化为GL文件格式(兼容原软件)"""
    lines = []
    header = f"    福彩3D霸主{issue}期过滤单-{seq:02d}  共{len(numbers)}注 (直选投注)  "
    lines.append(header)
    for n in numbers:
        lines.append(f"{n[0]}{n[1]}{n[2]}")
    return "\n".join(lines)
