"""
覆盖率自动过滤选择器
根据历史统计分布自动计算每个过滤条件的最优选值，不依赖AI判断。

核心算法：对每个条件，按频率从高到低累加，直到覆盖率>=目标阈值。
"""
import stats as st
import filter_engine as fe
from collections import Counter


# ============================================================
# 默认覆盖率目标（可通过回测自动调优）
# ============================================================
# 复盘优化: 质合比/和尾/重号/首尾差是主要杀手，提高覆盖率
DEFAULT_COVERAGE = {
    "奇偶比": 0.81,
    "大小比": 0.81,
    "质合比": 0.90,     # 3次杀手 → 提高
    "AC值": 0.81,
    "和值": 0.81,
    "跨度": 0.81,
    "连号": 0.84,
    "重号": 0.95,       # 重号=2占16% → 必须覆盖
    "首尾差": 0.88,     # 首尾差=7被漏 → 提高
    "和尾": 0.88,       # 2次杀手 → 提高
    "遗漏总值": 0.85,
    "012路": 0.83,
    "相邻号码": 0.84,
}

# 注数阈值：过滤后超过此注数则建议跳过
MAX_BET_NOTES = 100


def select_by_coverage(counter_dict, target=0.90, min_select=1):
    """
    按频率从高到低选，直到累计覆盖率 >= target。

    参数:
        counter_dict: {选项: 出现次数} 如 {"1:2": 22, "2:1": 21, "0:3": 4}
        target: 目标覆盖率 (0.0~1.0)
        min_select: 最少选几个
    返回:
        selected: 选中的选项列表
    """
    if not counter_dict:
        return []

    total = sum(counter_dict.values())
    if total == 0:
        return list(counter_dict.keys())

    # 按频率降序排列
    sorted_items = sorted(counter_dict.items(), key=lambda x: x[1], reverse=True)

    selected = []
    cumulative = 0
    for key, count in sorted_items:
        selected.append(key)
        cumulative += count
        if len(selected) >= min_select and cumulative / total >= target:
            break

    return selected


def build_auto_conditions(data, n_recent=50, coverage_targets=None):
    """
    基于历史统计分布，自动计算所有过滤条件。

    参数:
        data: 历史开奖数据列表
        n_recent: 参考最近多少期
        coverage_targets: 可选的覆盖率覆盖 {条件名: 覆盖率}
    返回:
        dict: 和 ai_engine.parse_filter_json() 格式完全兼容的条件字典
    """
    targets = dict(DEFAULT_COVERAGE)
    if coverage_targets:
        targets.update(coverage_targets)

    full_stats = st.build_full_stats(data, n_recent)
    last = data[-1]
    prev_nums = [last["d1"], last["d2"], last["d3"]]

    # 计算下一期期号
    next_issue = str(int(last["issue"]) + 1)

    # ========== 读取排除选项 ==========
    import config as _cfg
    excludes = getattr(_cfg, "EXCLUDE_OPTIONS", {})

    # ========== 逐条件自动选择 ==========

    # 1. 奇偶比
    oe_selected = [v for v in select_by_coverage(full_stats["奇偶比分布"], targets["奇偶比"])
                   if v not in excludes.get("奇偶比", [])]

    # 2. 大小比
    bs_selected = [v for v in select_by_coverage(full_stats["大小比分布"], targets["大小比"])
                   if v not in excludes.get("大小比", [])]

    # 3. 质合比
    pc_selected = [v for v in select_by_coverage(full_stats.get("质合比分布", {}), targets["质合比"])
                   if v not in excludes.get("质合比", [])]

    # 4. AC值
    ac_raw = select_by_coverage(full_stats["AC值分布"], targets["AC值"])
    ac_selected = [int(v) for v in ac_raw]

    # 5. 和值 (结合 Howard 70%法则)
    sum_raw = select_by_coverage(full_stats["和值分布"], targets["和值"])
    sum_coverage = sorted([int(v) for v in sum_raw])
    # Howard: 70%中奖落在最窄连续区间
    howard_zone = full_stats.get("Howard和值区间", {})
    if howard_zone and howard_zone.get("zone_low") is not None:
        zone_sums = list(range(howard_zone["zone_low"], howard_zone["zone_high"] + 1))
        # 取交集: 既在Howard区间内又是高频值 → 更精准
        # 但至少保留覆盖率选出的值，避免过窄
        sum_selected = sorted(set(sum_coverage) & set(zone_sums))
        if len(sum_selected) < 6:  # 交集太少，用并集
            sum_selected = sorted(set(sum_coverage) | set(zone_sums))
    else:
        sum_selected = sum_coverage

    # 6. 跨度
    span_raw = select_by_coverage(full_stats["跨度分布"], targets["跨度"])
    span_selected = sorted([int(v) for v in span_raw])

    # 7. 连号
    consec_raw = select_by_coverage(full_stats["连号分布"], targets["连号"])
    consec_selected = sorted([int(v) for v in consec_raw])

    # 8. 重号
    repeat_raw = select_by_coverage(
        full_stats.get("重号分布", {}), targets["重号"]
    )
    repeat_selected = sorted([int(v) for v in repeat_raw])

    # 9. 首尾差
    htd_raw = select_by_coverage(
        full_stats.get("首尾差分布", {}), targets["首尾差"]
    )
    htd_selected = sorted([int(v) for v in htd_raw])

    # 10. 和尾
    st_raw = select_by_coverage(
        full_stats.get("和尾分布", {}), targets["和尾"]
    )
    st_selected = sorted([int(v) for v in st_raw])

    # 11. 遗漏总值 (特殊：key是"5-9"格式的区间字符串，转为[[5,9],...]格式)
    mt_raw = select_by_coverage(
        full_stats.get("遗漏总值分布", {}), targets["遗漏总值"]
    )
    mt_selected = []
    for r in mt_raw:
        parts = r.split("-")
        if len(parts) == 2:
            mt_selected.append([int(parts[0]), int(parts[1])])
    mt_selected.sort(key=lambda x: x[0])

    # 12. 012路 (用全部分布，不只TOP10)
    road_dist = full_stats.get("012路分布全部", full_stats.get("012路分布TOP10", {}))
    road_selected = select_by_coverage(road_dist, targets["012路"])

    # ========== Howard: 偏差回归 ==========
    import config as _cfg
    bias = full_stats.get("偏差回归", {})
    if getattr(_cfg, "HOWARD_BIAS_ENABLED", True) and bias:
        # 奇偶比回归
        oe_bias = bias.get("odd_even", {})
        if oe_bias.get("revert"):
            for r in oe_bias.get("recommendations", []):
                if r not in oe_selected and r not in excludes.get("奇偶比", []):
                    oe_selected.append(r)
        # 大小比回归
        bs_bias = bias.get("big_small", {})
        if bs_bias.get("revert"):
            for r in bs_bias.get("recommendations", []):
                if r not in bs_selected and r not in excludes.get("大小比", []):
                    bs_selected.append(r)

    # ========== Howard: 相邻号码 ==========
    adj_condition = {}
    adj_stats = full_stats.get("相邻号码统计", {})
    if getattr(_cfg, "HOWARD_ADJACENT_ENABLED", True) and adj_stats:
        adj_dist = adj_stats.get("分布", {})
        adj_pool = adj_stats.get("当前相邻池", [])
        if adj_dist and adj_pool:
            adj_counts_raw = select_by_coverage(adj_dist, targets.get("相邻号码", 0.84))
            adj_min_counts = sorted([int(v) for v in adj_counts_raw])
            adj_condition = {"邻数集合": adj_pool, "最少包含": adj_min_counts}

    # ========== Howard: 跳期分析 (默认关闭) ==========
    skip_condition = {}
    if getattr(_cfg, "HOWARD_SKIP_HIT_ENABLED", False):
        skip_data = full_stats.get("跳期分析", {})
        if skip_data:
            skip_condition = {}
            for pos in ["百位", "十位", "个位"]:
                pos_data = skip_data.get(pos, {})
                # 选due_ratio >= 0.7 或 current_skip <= 3 的数字
                eligible = [d for d in range(10)
                            if pos_data.get(d, {}).get("due_ratio", 0) >= 0.7
                            or pos_data.get(d, {}).get("current", 99) <= 3]
                if len(eligible) >= 6:  # 至少保留6个，否则太激进
                    skip_condition[pos] = eligible

    # ========== Howard: 伴随号码 (默认关闭) ==========
    must_contain = []
    if getattr(_cfg, "HOWARD_COMPANION_ENABLED", False):
        comp = full_stats.get("伴随号码", {})
        strong = comp.get("strong_candidate")
        if strong is not None:
            must_contain = [strong]

    # ========== 组装 filters dict ==========
    filters = {
        "百位": [],
        "十位": [],
        "个位": [],
        "重号": {"上期号码": prev_nums, "重号数": repeat_selected},
        "相邻号码": adj_condition,
        "奇偶比": oe_selected,
        "大小比": bs_selected,
        "质合比": pc_selected,
        "AC值": ac_selected,
        "和值": sum_selected,
        "连号": consec_selected,
        "和尾": st_selected,
        "遗漏总值": mt_selected,
        "跨度": span_selected,
        "首尾差": htd_selected,
        "012路": road_selected,
        "组选类型": [],
        "必含号码": must_contain,
    }
    if skip_condition:
        filters["跳期过滤"] = skip_condition

    # 生成选择理由
    total_periods = n_recent
    reasons = []
    for name, dist_key, selected in [
        ("奇偶比", "奇偶比分布", oe_selected),
        ("大小比", "大小比分布", bs_selected),
        ("质合比", "质合比分布", pc_selected),
        ("AC值", "AC值分布", ac_raw),
        ("和值", "和值分布", sum_raw),
        ("跨度", "跨度分布", span_raw),
        ("连号", "连号分布", consec_raw),
        ("重号", "重号分布", repeat_raw),
    ]:
        dist = full_stats.get(dist_key, {})
        if dist and selected:
            covered = sum(dist.get(v, 0) for v in selected)
            pct = covered / total_periods * 100
            reasons.append(
                f"{name}: 选{len(selected)}项, 覆盖{covered}/{total_periods}={pct:.0f}%"
            )

    return {
        "filters": filters,
        "analysis": f"覆盖率自动选择(近{n_recent}期), 不杀号, 纯统计过滤",
        "confidence": "中",
        "key_reasons": reasons,
        "risk_notes": ["纯统计方法，无法预测突变", "覆盖率越高注数越多，需平衡"],
        "target_issue": next_issue,
    }


# ============================================================
# 回测
# ============================================================

def backtest(data, n_recent=50, coverage_targets=None, test_periods=100):
    """
    回测自动过滤策略的命中率。

    对最近 test_periods 期逐一测试：
      用该期之前的数据生成过滤条件 → 检查该期开奖是否在过滤结果中

    返回:
        dict: hits, total, hit_rate, avg_notes, details
    """
    if len(data) < n_recent + test_periods:
        test_periods = len(data) - n_recent - 1

    hits = 0
    total = 0
    note_counts = []
    details = []

    for i in range(len(data) - test_periods, len(data)):
        history = data[:i]
        actual = data[i]
        actual_tuple = (actual["d1"], actual["d2"], actual["d3"])

        # 用历史数据生成自动过滤条件
        result = build_auto_conditions(history, n_recent, coverage_targets)
        filters = result["filters"]

        # 计算遗漏值
        missing_data = st.calc_missing_values(history)

        # 上一期号码
        prev = [history[-1]["d1"], history[-1]["d2"], history[-1]["d3"]]
        # 重号需要用当前的上期号码
        filters["重号"]["上期号码"] = prev

        # 执行过滤
        numbers, _ = fe.apply_filters(filters, prev, missing_data=missing_data)
        count = len(numbers)
        hit = actual_tuple in numbers

        if hit:
            hits += 1
        total += 1
        note_counts.append(count)

        details.append({
            "issue": actual["issue"],
            "actual": f"{actual['d1']}{actual['d2']}{actual['d3']}",
            "notes": count,
            "hit": hit,
        })

    avg_notes = sum(note_counts) / len(note_counts) if note_counts else 0

    return {
        "hits": hits,
        "total": total,
        "hit_rate": f"{hits / total * 100:.1f}%" if total > 0 else "N/A",
        "hit_rate_num": hits / total if total > 0 else 0,
        "avg_notes": f"{avg_notes:.0f}",
        "avg_notes_num": avg_notes,
        "min_notes": min(note_counts) if note_counts else 0,
        "max_notes": max(note_counts) if note_counts else 0,
        "details": details,
    }


def optimize_coverage(data, n_recent=50, test_periods=50,
                      target_notes=(60, 120)):
    """
    搜索最优全局覆盖率，使命中率最大且平均注数在目标范围内。

    测试覆盖率从 0.80 到 0.95，步长 0.02
    """
    best = None
    results = []

    for cov_pct in range(80, 96, 2):
        cov = cov_pct / 100.0
        # 所有条件使用同一个覆盖率
        targets = {k: cov for k in DEFAULT_COVERAGE}
        # 012路比较特殊，可能值多，用更低覆盖率
        targets["012路"] = max(cov - 0.05, 0.70)

        result = backtest(data, n_recent, targets, test_periods)
        avg = result["avg_notes_num"]
        hr = result["hit_rate_num"]

        in_range = target_notes[0] <= avg <= target_notes[1]
        results.append({
            "coverage": cov,
            "hit_rate": result["hit_rate"],
            "avg_notes": result["avg_notes"],
            "in_range": in_range,
        })

        if in_range and (best is None or hr > best["hit_rate_num"]):
            best = {
                "coverage": cov,
                "hit_rate": result["hit_rate"],
                "hit_rate_num": hr,
                "avg_notes": result["avg_notes"],
                "avg_notes_num": avg,
                "targets": targets,
            }

    return {
        "best": best,
        "all_results": results,
    }
