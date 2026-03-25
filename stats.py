"""
统计分析模块 - 计算各种指标，为AI提供结构化数据
"""
from collections import Counter, defaultdict
from itertools import combinations


def calc_sum(d1, d2, d3):
    return d1 + d2 + d3


def calc_span(d1, d2, d3):
    return max(d1, d2, d3) - min(d1, d2, d3)


def calc_ac(d1, d2, d3):
    nums = [d1, d2, d3]
    diffs = set()
    for a, b in combinations(nums, 2):
        diffs.add(abs(a - b))
    return len(diffs)


def calc_odd_even(d1, d2, d3):
    odd = sum(1 for x in [d1, d2, d3] if x % 2 == 1)
    return f"{odd}:{3 - odd}"


def calc_big_small(d1, d2, d3):
    big = sum(1 for x in [d1, d2, d3] if x >= 5)
    return f"{big}:{3 - big}"


def calc_012_road(d1, d2, d3):
    return f"{d1 % 3}{d2 % 3}{d3 % 3}"


def calc_prime_composite(d1, d2, d3):
    primes = {1, 2, 3, 5, 7}  # 3D中1算质数
    p = sum(1 for x in [d1, d2, d3] if x in primes)
    return f"{p}:{3 - p}"


def calc_repeat_with_prev(curr, prev):
    """计算与上期重号数"""
    if prev is None:
        return 0
    curr_set = [curr["d1"], curr["d2"], curr["d3"]]
    prev_set = [prev["d1"], prev["d2"], prev["d3"]]
    count = 0
    prev_copy = prev_set.copy()
    for c in curr_set:
        if c in prev_copy:
            count += 1
            prev_copy.remove(c)
    return count


def get_group_type(d1, d2, d3):
    """组选类型"""
    s = {d1, d2, d3}
    if len(s) == 3:
        return "组六"
    elif len(s) == 2:
        return "组三"
    else:
        return "豹子"


def calc_missing_values(data, n_recent=None):
    """计算号码遗漏值"""
    if n_recent:
        data = data[-n_recent:]

    missing = {"百位": {}, "十位": {}, "个位": {}}
    for pos_name, key in [("百位", "d1"), ("十位", "d2"), ("个位", "d3")]:
        for digit in range(10):
            # 找最后一次出现的位置
            last_seen = -1
            for i, d in enumerate(data):
                if d[key] == digit:
                    last_seen = i
            if last_seen == -1:
                missing[pos_name][digit] = len(data)
            else:
                missing[pos_name][digit] = len(data) - 1 - last_seen
    return missing


def calc_hot_cold(data, n_recent=30):
    """计算热温冷号"""
    recent = data[-n_recent:]
    freq = {"百位": Counter(), "十位": Counter(), "个位": Counter()}
    for d in recent:
        freq["百位"][d["d1"]] += 1
        freq["十位"][d["d2"]] += 1
        freq["个位"][d["d3"]] += 1

    result = {}
    for pos in ["百位", "十位", "个位"]:
        avg = n_recent / 10  # 平均出现次数
        hot = [k for k, v in freq[pos].items() if v >= avg * 1.5]
        warm = [k for k, v in freq[pos].items() if avg * 0.5 <= v < avg * 1.5]
        cold = [k for k in range(10) if k not in hot and k not in warm]
        result[pos] = {"热": sorted(hot), "温": sorted(warm), "冷": sorted(cold)}
    return result


def calc_number_frequency(data, n_recent=50):
    """号码出现频率"""
    recent = data[-n_recent:]
    freq = {"百位": Counter(), "十位": Counter(), "个位": Counter()}
    for d in recent:
        freq["百位"][d["d1"]] += 1
        freq["十位"][d["d2"]] += 1
        freq["个位"][d["d3"]] += 1
    return freq


def calc_sum_distribution(data, n_recent=50):
    """和值分布"""
    recent = data[-n_recent:]
    sums = [calc_sum(d["d1"], d["d2"], d["d3"]) for d in recent]
    return Counter(sums)


def calc_span_distribution(data, n_recent=50):
    """跨度分布"""
    recent = data[-n_recent:]
    spans = [calc_span(d["d1"], d["d2"], d["d3"]) for d in recent]
    return Counter(spans)


def calc_consecutive_patterns(data, n_recent=30):
    """连号规律"""
    recent = data[-n_recent:]
    patterns = []
    for d in recent:
        nums = sorted([d["d1"], d["d2"], d["d3"]])
        consec = 0
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consec += 1
        patterns.append(consec)
    return Counter(patterns)


def build_full_stats(data, n_recent=50):
    """构建完整统计数据，供AI分析"""
    recent = data[-n_recent:]
    stats = {}

    # 1. 基础信息
    stats["总期数"] = len(data)
    stats["分析期数"] = n_recent
    stats["最新期号"] = data[-1]["issue"] if data else "无"

    # 2. 最近N期详细数据
    stats["近期开奖"] = []
    for i, d in enumerate(recent):
        s = calc_sum(d["d1"], d["d2"], d["d3"])
        sp = calc_span(d["d1"], d["d2"], d["d3"])
        ac = calc_ac(d["d1"], d["d2"], d["d3"])
        oe = calc_odd_even(d["d1"], d["d2"], d["d3"])
        bs = calc_big_small(d["d1"], d["d2"], d["d3"])
        road = calc_012_road(d["d1"], d["d2"], d["d3"])
        gt = get_group_type(d["d1"], d["d2"], d["d3"])
        prev = recent[i - 1] if i > 0 else (data[-n_recent - 1] if len(data) > n_recent else None)
        repeat = calc_repeat_with_prev(d, prev)
        stats["近期开奖"].append({
            "期号": d["issue"],
            "号码": f"{d['d1']}{d['d2']}{d['d3']}",
            "和值": s, "跨度": sp, "AC值": ac,
            "奇偶比": oe, "大小比": bs,
            "012路": road, "组选类型": gt,
            "重号数": repeat,
        })

    # 3. 号码频率
    stats["号码频率"] = {}
    freq = calc_number_frequency(data, n_recent)
    for pos in ["百位", "十位", "个位"]:
        stats["号码频率"][pos] = {str(k): v for k, v in sorted(freq[pos].items())}

    # 4. 遗漏值
    stats["当前遗漏"] = calc_missing_values(data)

    # 5. 热温冷号
    stats["热温冷号"] = calc_hot_cold(data, min(n_recent, 30))

    # 6. 和值分布
    sum_dist = calc_sum_distribution(data, n_recent)
    stats["和值分布"] = {str(k): v for k, v in sorted(sum_dist.items())}

    # 7. 跨度分布
    span_dist = calc_span_distribution(data, n_recent)
    stats["跨度分布"] = {str(k): v for k, v in sorted(span_dist.items())}

    # 8. 奇偶比分布
    oe_counts = Counter()
    for d in recent:
        oe_counts[calc_odd_even(d["d1"], d["d2"], d["d3"])] += 1
    stats["奇偶比分布"] = dict(oe_counts.most_common())

    # 9. 大小比分布
    bs_counts = Counter()
    for d in recent:
        bs_counts[calc_big_small(d["d1"], d["d2"], d["d3"])] += 1
    stats["大小比分布"] = dict(bs_counts.most_common())

    # 10. 012路分布
    road_counts = Counter()
    for d in recent:
        road_counts[calc_012_road(d["d1"], d["d2"], d["d3"])] += 1
    stats["012路分布TOP10"] = dict(road_counts.most_common(10))

    # 11. AC值分布
    ac_counts = Counter()
    for d in recent:
        ac_counts[calc_ac(d["d1"], d["d2"], d["d3"])] += 1
    stats["AC值分布"] = dict(ac_counts.most_common())

    # 12. 组选类型分布
    gt_counts = Counter()
    for d in recent:
        gt_counts[get_group_type(d["d1"], d["d2"], d["d3"])] += 1
    stats["组选类型分布"] = dict(gt_counts.most_common())

    # 13. 连号分布
    stats["连号分布"] = dict(calc_consecutive_patterns(data, n_recent).most_common())

    # 14. 趋势信号 (最近10期的变化)
    last10 = recent[-10:]
    stats["近10期趋势"] = {
        "和值走势": [calc_sum(d["d1"], d["d2"], d["d3"]) for d in last10],
        "跨度走势": [calc_span(d["d1"], d["d2"], d["d3"]) for d in last10],
        "AC值走势": [calc_ac(d["d1"], d["d2"], d["d3"]) for d in last10],
    }

    return stats


def backtest_filter(data, filter_numbers_func, start_idx=100, end_idx=None):
    """回测过滤策略的命中率"""
    if end_idx is None:
        end_idx = len(data)

    hits = 0
    total = 0
    details = []

    for i in range(start_idx, end_idx):
        history = data[:i]
        actual = data[i]
        predicted_set = filter_numbers_func(history)

        actual_tuple = (actual["d1"], actual["d2"], actual["d3"])
        hit = actual_tuple in predicted_set

        if hit:
            hits += 1
        total += 1

        details.append({
            "issue": actual["issue"],
            "actual": actual_tuple,
            "predicted_count": len(predicted_set),
            "hit": hit,
        })

    return {
        "total": total,
        "hits": hits,
        "hit_rate": f"{hits / total * 100:.1f}%" if total > 0 else "N/A",
        "details": details,
    }
