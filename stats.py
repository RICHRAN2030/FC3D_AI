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
    stats["012路分布全部"] = dict(road_counts.most_common())

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

    # 14. 质合比分布
    pc_counts = Counter()
    for d in recent:
        pc_counts[calc_prime_composite(d["d1"], d["d2"], d["d3"])] += 1
    stats["质合比分布"] = dict(pc_counts.most_common())

    # 15. 重号分布 (与上期重复号码个数)
    repeat_counts = Counter()
    for i, d in enumerate(recent):
        prev = recent[i - 1] if i > 0 else (data[-n_recent - 1] if len(data) > n_recent else None)
        repeat_counts[calc_repeat_with_prev(d, prev)] += 1
    stats["重号分布"] = dict(sorted(repeat_counts.items()))

    # 16. 首尾差分布 (百位-个位的绝对值)
    htd_counts = Counter()
    for d in recent:
        htd_counts[abs(d["d1"] - d["d3"])] += 1
    stats["首尾差分布"] = dict(sorted(htd_counts.items()))

    # 17. 和尾分布 (和值个位数)
    st_counts = Counter()
    for d in recent:
        st_counts[(d["d1"] + d["d2"] + d["d3"]) % 10] += 1
    stats["和尾分布"] = dict(sorted(st_counts.items()))

    # 18. 遗漏总值分布 (百位遗漏+十位遗漏+个位遗漏，按区间统计)
    missing = stats["当前遗漏"]  # 已经在前面计算过
    # 用全部数据计算每期的遗漏总值
    all_missing = calc_missing_values(data)
    mt_counts = Counter()
    for d in recent:
        # 计算该号码在当期之前的遗漏值之和(近似用当前遗漏值)
        mt = all_missing["百位"].get(d["d1"], 0) + all_missing["十位"].get(d["d2"], 0) + all_missing["个位"].get(d["d3"], 0)
        # 按5为步长分区间
        bucket = (mt // 5) * 5
        mt_counts[f"{bucket}-{bucket+4}"] += 1
    stats["遗漏总值分布"] = dict(sorted(mt_counts.items(), key=lambda x: int(x[0].split('-')[0])))

    # 19. 趋势信号 (最近10期的变化)
    last10 = recent[-10:]
    stats["近10期趋势"] = {
        "和值走势": [calc_sum(d["d1"], d["d2"], d["d3"]) for d in last10],
        "跨度走势": [calc_span(d["d1"], d["d2"], d["d3"]) for d in last10],
        "AC值走势": [calc_ac(d["d1"], d["d2"], d["d3"]) for d in last10],
    }

    # ========== Howard 策略统计 ==========

    # 20. Howard 70%和值区间
    stats["Howard和值区间"] = calc_howard_sum_zone(data, max(n_recent, 100))

    # 21. 偏差回归
    stats["偏差回归"] = calc_bias_tracker(data, min(n_recent, 30))

    # 22. 相邻号码统计
    stats["相邻号码统计"] = calc_adjacent_stats(data, n_recent)

    # 23. 跳期分析
    stats["跳期分析"] = calc_skip_hit(data, max(n_recent, 100))

    # 24. 伴随号码
    stats["伴随号码"] = calc_companion_matrix(data, max(n_recent, 100))

    return stats


# ============================================================
# Howard 策略统计函数
# ============================================================

def calc_howard_sum_zone(data, n_recent=100, target_pct=0.70):
    """
    Howard 70%法则: 找到覆盖70%开奖的最窄连续和值区间。
    用滑动窗口从最窄宽度开始搜索。
    """
    recent = data[-n_recent:]
    sums = [d["d1"] + d["d2"] + d["d3"] for d in recent]
    total = len(sums)
    target_count = int(total * target_pct)

    # 和值分布 (0-27)
    dist = Counter(sums)

    best_low, best_high, best_width = 0, 27, 28
    # 从最小窗口宽度开始搜索
    for width in range(1, 28):
        for low in range(0, 28 - width):
            high = low + width
            count = sum(dist.get(s, 0) for s in range(low, high + 1))
            if count >= target_count and width < best_width:
                best_low, best_high, best_width = low, high, width
                break  # 找到该宽度的最优起点就跳到下一个宽度
        if best_width <= width:
            break  # 已找到最窄窗口

    covered = sum(dist.get(s, 0) for s in range(best_low, best_high + 1))
    return {
        "zone_low": best_low,
        "zone_high": best_high,
        "zone_width": best_high - best_low + 1,
        "coverage": covered / total if total > 0 else 0,
        "covered_count": covered,
        "total": total,
    }


def calc_bias_tracker(data, n_recent=30):
    """
    Howard 偏差回归: 双窗口检测奇偶比/大小比/和值偏差。
    当短期(10期)和中期(20期)都偏离均值 → 预测回归。
    """
    result = {}

    for name, calc_fn, expected in [
        ("odd_even", lambda d: sum(1 for x in [d["d1"], d["d2"], d["d3"]] if x % 2 == 1), 1.5),
        ("big_small", lambda d: sum(1 for x in [d["d1"], d["d2"], d["d3"]] if x >= 5), 1.5),
    ]:
        recent10 = data[-10:]
        recent20 = data[-20:]

        avg10 = sum(calc_fn(d) for d in recent10) / len(recent10)
        avg20 = sum(calc_fn(d) for d in recent20) / len(recent20)

        # 偏差方向
        bias10 = "偏高" if avg10 > expected + 0.3 else ("偏低" if avg10 < expected - 0.3 else "均衡")
        bias20 = "偏高" if avg20 > expected + 0.2 else ("偏低" if avg20 < expected - 0.2 else "均衡")

        # 回归信号: 两个窗口同方向偏离
        revert = bias10 != "均衡" and bias10 == bias20

        # 推荐
        recommendations = []
        if name == "odd_even":
            if revert and bias10 == "偏高":
                recommendations = ["0:3", "1:2"]  # 偏奇 → 推偶
            elif revert and bias10 == "偏低":
                recommendations = ["3:0", "2:1"]  # 偏偶 → 推奇
        elif name == "big_small":
            if revert and bias10 == "偏高":
                recommendations = ["0:3", "1:2"]  # 偏大 → 推小
            elif revert and bias10 == "偏低":
                recommendations = ["3:0", "2:1"]  # 偏小 → 推大

        result[name] = {
            "avg10": round(avg10, 2),
            "avg20": round(avg20, 2),
            "bias10": bias10,
            "bias20": bias20,
            "revert": revert,
            "recommendations": recommendations,
        }

    # 和值偏差
    recent10 = data[-10:]
    recent20 = data[-20:]
    sum10 = sum(d["d1"] + d["d2"] + d["d3"] for d in recent10) / 10
    sum20 = sum(d["d1"] + d["d2"] + d["d3"] for d in recent20) / 20
    expected_sum = 13.5  # 理论均值

    result["sum"] = {
        "avg10": round(sum10, 1),
        "avg20": round(sum20, 1),
        "bias": "偏高" if sum10 > 16 and sum20 > 15 else ("偏低" if sum10 < 11 and sum20 < 12 else "正常"),
    }

    return result


def calc_adjacent_stats(data, n_recent=50):
    """
    Howard 相邻号码: 上期号码±1的数字下期出现概率更高。
    """
    recent = data[-n_recent:]
    hit_counts = Counter()

    for i in range(1, len(recent)):
        prev = recent[i - 1]
        curr = recent[i]
        # 上期号码的相邻数字池
        adj_pool = set()
        for d in [prev["d1"], prev["d2"], prev["d3"]]:
            adj_pool.add((d - 1) % 10)
            adj_pool.add((d + 1) % 10)
        # 本期号码命中几个相邻数字
        curr_digits = {curr["d1"], curr["d2"], curr["d3"]}
        hit_count = len(curr_digits & adj_pool)
        hit_counts[hit_count] += 1

    # 当前相邻池 (基于最新一期)
    last = data[-1]
    current_pool = set()
    for d in [last["d1"], last["d2"], last["d3"]]:
        current_pool.add((d - 1) % 10)
        current_pool.add((d + 1) % 10)

    return {
        "分布": dict(sorted(hit_counts.items())),
        "当前相邻池": sorted(current_pool),
    }


def calc_skip_hit(data, n_recent=100):
    """
    Howard 跳期分析: 每个位置每个数字的跳期规律。
    due_ratio = 当前跳期 / 平均跳期, >=0.8 表示"即将出现"
    """
    recent = data[-n_recent:]
    result = {}

    for pos_name, key in [("百位", "d1"), ("十位", "d2"), ("个位", "d3")]:
        pos_result = {}
        for digit in range(10):
            # 找到所有出现位置
            appearances = [i for i, d in enumerate(recent) if d[key] == digit]
            if len(appearances) < 2:
                avg_skip = n_recent  # 极少出现
            else:
                # 计算各次跳期
                skips = [appearances[j] - appearances[j - 1] for j in range(1, len(appearances))]
                avg_skip = sum(skips) / len(skips)

            # 当前跳期(距最后一次出现)
            current_skip = n_recent - 1 - appearances[-1] if appearances else n_recent

            due_ratio = current_skip / avg_skip if avg_skip > 0 else 0

            pos_result[digit] = {
                "avg_skip": round(avg_skip, 1),
                "current": current_skip,
                "due_ratio": round(due_ratio, 2),
            }
        result[pos_name] = pos_result

    return result


def calc_companion_matrix(data, n_recent=100):
    """
    Howard 伴随号码: 哪些数字经常一起出现。
    """
    recent = data[-n_recent:]

    # 10x10 共现矩阵
    matrix = [[0] * 10 for _ in range(10)]
    for d in recent:
        digits = [d["d1"], d["d2"], d["d3"]]
        for i in range(3):
            for j in range(i + 1, 3):
                a, b = digits[i], digits[j]
                matrix[a][b] += 1
                matrix[b][a] += 1

    # 每个数字的TOP3伴随
    top_companions = {}
    for digit in range(10):
        pairs = [(other, matrix[digit][other]) for other in range(10) if other != digit]
        pairs.sort(key=lambda x: x[1], reverse=True)
        top_companions[digit] = [(p[0], p[1]) for p in pairs[:3]]

    # 找强候选: 热号的共同高频伴随
    hot_cold = calc_hot_cold(data, min(n_recent, 30))
    hot_digits = set()
    for pos in ["百位", "十位", "个位"]:
        hot_digits.update(hot_cold[pos]["热"])

    # 统计哪个数字是最多热号的TOP3伴随
    companion_count = Counter()
    for hd in hot_digits:
        for comp, freq in top_companions.get(hd, []):
            companion_count[comp] += 1

    strong = None
    if companion_count:
        best_digit, best_count = companion_count.most_common(1)[0]
        if best_count >= 2:  # 至少是2个热号的TOP3伴随
            strong = best_digit

    return {
        "top_companions": {str(k): v for k, v in top_companions.items()},
        "strong_candidate": strong,
    }


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
