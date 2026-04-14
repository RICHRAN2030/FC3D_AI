"""
FC3D_AI - 福彩3D AI智能分析系统
主程序入口
"""
import sys
import os

if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import data_manager as dm
import ai_engine as ai
import filter_engine as fe
import stats as st
import scheduler
import json


def print_banner():
    print("=" * 55)
    print("       FC3D_AI - 福彩3D AI智能分析系统")
    print("       Claude大模型 + 自动过滤 + 定时复盘")
    print("=" * 55)


def print_menu():
    print()
    print("┌────────────────────────────────────┐")
    mode = getattr(config, "FILTER_MODE", "auto")
    mode_label = "覆盖率自动" if mode == "auto" else "AI"
    print(f"│  1. ★ 一键过滤出号 [{mode_label}]        │")
    print("│  s. ★ 半自动过滤 (逐步确认)          │")
    print("│  2. AI详细分析报告                  │")
    print("│  3. 复盘过滤结果                    │")
    print("│  4. 批量复盘统计                    │")
    print("│  5. 自由提问                        │")
    print("│  6. 数据统计总览                    │")
    print("│  7. 更新开奖数据                    │")
    print("│  8. 手动录入数据                    │")
    print("│  9. 设置                            │")
    print("│  ──────────────────────────────────│")
    print("│  b. 回测自动过滤 (验证命中率)        │")
    print("│  d. 立即执行每日定时任务             │")
    print("│  t. 安装/卸载Windows定时任务         │")
    print("│  0. 退出                            │")
    print("└────────────────────────────────────┘")


def check_api_key():
    if config.API_PROVIDER == "poe":
        key = config.POE_API_KEY or os.environ.get("POE_API_KEY", "")
    else:
        key = config.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print(f"\n[!] 未设置 {config.API_PROVIDER.upper()} API Key → 菜单9设置")
        return False
    model = config.POE_MODEL if config.API_PROVIDER == "poe" else config.ANTHROPIC_MODEL
    print(f"[AI: {config.API_PROVIDER.upper()} / {model}]")
    return True


def get_gl_dir():
    gl_dir = os.path.join(config.OUTPUT_DIR, "gl")
    os.makedirs(gl_dir, exist_ok=True)
    return gl_dir


def show_stats(data):
    if not data:
        print("无数据")
        return
    print(f"\n数据: {len(data)}期 ({data[0]['issue']} ~ {data[-1]['issue']})")
    print("\n最近10期:")
    print(f"{'期号':>9} {'号码':>5} {'和值':>4} {'跨度':>4} {'AC':>3} {'奇偶':>5} {'大小':>5} {'012':>4} {'类型':>4}")
    print("-" * 55)
    for d in data[-10:]:
        s, sp = st.calc_sum(d["d1"], d["d2"], d["d3"]), st.calc_span(d["d1"], d["d2"], d["d3"])
        ac = st.calc_ac(d["d1"], d["d2"], d["d3"])
        oe, bs = st.calc_odd_even(d["d1"], d["d2"], d["d3"]), st.calc_big_small(d["d1"], d["d2"], d["d3"])
        road, gt = st.calc_012_road(d["d1"], d["d2"], d["d3"]), st.get_group_type(d["d1"], d["d2"], d["d3"])
        print(f"{d['issue']:>9} {d['d1']}{d['d2']}{d['d3']:>3}  {s:>4} {sp:>4} {ac:>3} {oe:>5} {bs:>5} {road:>4} {gt:>4}")

    missing = st.calc_missing_values(data)
    print("\n遗漏值:")
    print(f"{'':>4}", end="")
    for i in range(10):
        print(f"{i:>5}", end="")
    print()
    for pos in ["百位", "十位", "个位"]:
        print(f"{pos:>4}", end="")
        for i in range(10):
            print(f"{missing[pos].get(i, 0):>5}", end="")
        print()

    hc = st.calc_hot_cold(data, 30)
    print("\n热温冷 (近30期):")
    for pos in ["百位", "十位", "个位"]:
        print(f"  {pos}: 热{hc[pos]['热']}  温{hc[pos]['温']}  冷{hc[pos]['冷']}")


def func_backtest(data):
    """回测自动过滤策略"""
    import auto_select

    n = input("回测期数 (默认100): ").strip()
    test_periods = int(n) if n.isdigit() else 100

    print(f"\n回测最近{test_periods}期...")
    print("(每期用该期之前的数据生成过滤条件，检查是否命中)\n")

    result = auto_select.backtest(data, config.DEFAULT_RECENT_PERIODS,
                                   test_periods=test_periods)

    print(f"{'='*50}")
    print(f"  命中率: {result['hits']}/{result['total']} = {result['hit_rate']}")
    print(f"  平均注数: {result['avg_notes']}")
    print(f"  注数范围: {result['min_notes']} ~ {result['max_notes']}")
    print(f"{'='*50}")

    # 显示最近20期详情
    print(f"\n最近20期详情:")
    print(f"  {'期号':>10} {'开奖':>6} {'注数':>6} {'结果':>6}")
    print(f"  {'─'*35}")
    for d in result["details"][-20:]:
        status = "✓命中" if d["hit"] else "✗未中"
        print(f"  {d['issue']:>10} {d['actual']:>6} {d['notes']:>6} {status}")

    # 问是否优化
    opt = input("\n是否搜索最优覆盖率? (y/N): ").strip().lower()
    if opt == "y":
        print("\n搜索中 (测试覆盖率0.80~0.95)...")
        opt_result = auto_select.optimize_coverage(
            data, config.DEFAULT_RECENT_PERIODS,
            test_periods=min(test_periods, 50)
        )
        print(f"\n{'覆盖率':>8} {'命中率':>8} {'平均注数':>8} {'范围内':>6}")
        print(f"{'─'*36}")
        for r in opt_result["all_results"]:
            mark = "  ★" if r["in_range"] else ""
            print(f"  {r['coverage']:.0%}    {r['hit_rate']:>8} {r['avg_notes']:>8}{mark}")

        if opt_result["best"]:
            b = opt_result["best"]
            print(f"\n推荐: 覆盖率{b['coverage']:.0%}, 命中率{b['hit_rate']}, 平均{b['avg_notes']}注")


def func_semi_auto_filter(data):
    """半自动模式：逐步过滤，每步显示建议+理由，用户确认或修改"""
    import auto_select

    n_recent = config.DEFAULT_RECENT_PERIODS
    last = data[-1]
    prev_nums = [last["d1"], last["d2"], last["d3"]]
    next_issue = str(int(last["issue"]) + 1)

    print(f"\n{'='*50}")
    print(f"  半自动过滤 → {next_issue}期")
    print(f"  上期: {last['issue']}期 {last['d1']}{last['d2']}{last['d3']}")
    print(f"{'='*50}")

    # 计算统计数据
    full_stats = st.build_full_stats(data, n_recent)
    missing_data = st.calc_missing_values(data)

    # 获取自动推荐条件
    auto_result = auto_select.build_auto_conditions(data, n_recent)
    auto_filters = auto_result["filters"]

    # 逐步过滤的步骤定义
    # (步骤名, 条件key, 分布数据key, 格式化函数)
    steps = [
        ("重号", "重号", "重号分布",
         lambda f: f"上期{prev_nums}, 重号数{f.get('重号数', [])}",
         lambda dist: "  ".join(f"{k}重号:{v}次" for k, v in sorted(dist.items()))),
        ("相邻号码", "相邻号码", "相邻号码统计",
         lambda f: f"相邻池{f.get('邻数集合', [])}, 最少{f.get('最少包含', [])}个",
         lambda s: f"命中分布: " + "  ".join(f"{k}个:{v}次" for k, v in sorted(s.get('分布', {}).items()))),
        ("奇偶比", "奇偶比", "奇偶比分布",
         lambda f: ", ".join(f),
         lambda dist: "  ".join(f"{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True))),
        ("大小比", "大小比", "大小比分布",
         lambda f: ", ".join(f),
         lambda dist: "  ".join(f"{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True))),
        ("质合比", "质合比", "质合比分布",
         lambda f: ", ".join(f),
         lambda dist: "  ".join(f"{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True))),
        ("AC值", "AC值", "AC值分布",
         lambda f: ", ".join(str(x) for x in f),
         lambda dist: "  ".join(f"AC{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True))),
        ("和值", "和值", "和值分布",
         lambda f: str(f),
         lambda dist: "TOP: " + ", ".join(f"{k}({v}次)" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True)[:12])),
        ("连号", "连号", "连号分布",
         lambda f: ", ".join(str(x) for x in f),
         lambda dist: "  ".join(f"{k}连号:{v}次" for k, v in sorted(dist.items()))),
        ("和尾", "和尾", "和尾分布",
         lambda f: ", ".join(str(x) for x in f),
         lambda dist: "  ".join(f"{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True))),
        ("遗漏总值", "遗漏总值", "遗漏总值分布",
         lambda f: str(f),
         lambda dist: "  ".join(f"{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: int(x[0].split('-')[0])))),
        ("跨度", "跨度", "跨度分布",
         lambda f: ", ".join(str(x) for x in f),
         lambda dist: "  ".join(f"{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True))),
        ("首尾差", "首尾差", "首尾差分布",
         lambda f: ", ".join(str(x) for x in f),
         lambda dist: "  ".join(f"{k}:{v}次" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True))),
        ("012路", "012路", "012路分布全部",
         lambda f: ", ".join(f) if len(f) <= 10 else f"{len(f)}种",
         lambda dist: "TOP10: " + ", ".join(f"{k}({v}次)" for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True)[:10])),
    ]

    # 当前号码池
    numbers = fe.generate_all()
    final_filters = {}
    print(f"\n起始: {len(numbers)}注\n")

    for i, (step_name, key, dist_key, fmt_recommend, fmt_dist) in enumerate(steps, 1):
        recommend = auto_filters.get(key)
        if not recommend:
            continue

        # 获取分布数据
        dist = full_stats.get(dist_key, {})

        # 显示
        print(f"┌─ 步骤{i}: {step_name} {'─'*(35 - len(step_name)*2)}")
        if dist:
            print(f"│  统计: {fmt_dist(dist)}")
        print(f"│  建议: {fmt_recommend(recommend)}")

        # 模拟这一步的效果
        test_filters = {key: recommend}
        test_numbers = list(numbers)  # copy
        if key == "重号" and isinstance(recommend, dict):
            prev = recommend.get("上期号码", prev_nums)
            counts = recommend.get("重号数", [0, 1, 2])
            test_numbers = fe.filter_repeat_with_prev(test_numbers, prev, counts)
        elif key == "相邻号码" and isinstance(recommend, dict):
            test_numbers = fe.filter_adjacent(test_numbers, recommend)
        elif key == "遗漏总值" and isinstance(recommend, list):
            test_numbers = fe.filter_missing_total(test_numbers, recommend, missing_data)
        elif key in fe.FILTER_MAP:
            _, func = fe.FILTER_MAP[key]
            test_numbers = func(test_numbers, recommend)

        eliminated = len(numbers) - len(test_numbers)
        print(f"│  效果: {len(numbers)}注 → {len(test_numbers)}注 (淘汰{eliminated})")
        print(f"└─────────────────────────────────────")

        # 用户决策
        choice = input(f"  [Enter=确认] [s=跳过] [m=修改]: ").strip().lower()

        if choice == "s":
            print(f"  → 跳过{step_name}\n")
            continue
        elif choice == "m":
            if key in ("重号", "相邻号码", "遗漏总值"):
                print(f"  (此条件格式复杂，建议用Enter确认或s跳过)")
                choice = input(f"  [Enter=确认] [s=跳过]: ").strip().lower()
                if choice == "s":
                    print(f"  → 跳过{step_name}\n")
                    continue
            else:
                user_input = input(f"  输入新值(逗号分隔): ").strip()
                if user_input:
                    parts = [p.strip() for p in user_input.split(",")]
                    if key in ("AC值", "和值", "跨度", "连号", "和尾", "首尾差"):
                        try:
                            recommend = [int(p) for p in parts]
                        except ValueError:
                            print("  格式错误，使用建议值")
                    else:
                        recommend = parts
                    # 重新计算效果
                    test_numbers = list(numbers)
                    if key in fe.FILTER_MAP:
                        _, func = fe.FILTER_MAP[key]
                        test_numbers = func(test_numbers, recommend)
                    eliminated = len(numbers) - len(test_numbers)
                    print(f"  → 修改后: {len(numbers)}注 → {len(test_numbers)}注 (淘汰{eliminated})")

        # 应用这一步
        numbers = test_numbers
        final_filters[key] = recommend
        print(f"  ✓ 确认 → 剩余{len(numbers)}注\n")

        if len(numbers) <= 30:
            print(f"  ⚠ 已低于30注，停止过滤")
            break

    count = len(numbers)
    cost = count * 2
    print(f"\n{'='*50}")
    print(f"  最终结果: {count}注 | 成本: {cost}元")
    print(f"{'='*50}")

    if count == 0:
        print("0注，请调整条件重试")
        return

    # 保存
    save = input("\n保存为GL文件? (Y/n): ").strip().lower()
    if save == "n":
        return

    gl_dir = os.path.join(config.OUTPUT_DIR, "gl")
    os.makedirs(gl_dir, exist_ok=True)
    seq = 1
    while os.path.exists(os.path.join(gl_dir, f"GL{next_issue}-{seq:02d}.txt")):
        seq += 1
    gl_name = f"GL{next_issue}-{seq:02d}.txt"
    gl_content = fe.format_gl_output(numbers, next_issue, seq)
    with open(os.path.join(gl_dir, gl_name), "w", encoding="gb18030") as f:
        f.write(gl_content)
    print(f"已保存: {gl_name}")

    # 显示号码
    cols = 10
    print(f"\n{count}注号码:")
    for i in range(0, count, cols):
        row = numbers[i:i+cols]
        print("  " + " ".join(f"{n[0]}{n[1]}{n[2]}" for n in row))


def func_auto_filter(data):
    mode = getattr(config, "FILTER_MODE", "auto")
    n = input(f"参考期数 (默认{config.DEFAULT_RECENT_PERIODS}): ").strip()
    n_recent = int(n) if n.isdigit() else config.DEFAULT_RECENT_PERIODS
    n_recent = min(n_recent, config.MAX_CONTEXT_PERIODS)

    last = data[-1]
    print(f"\n最新: {last['issue']}期 {last['d1']}{last['d2']}{last['d3']}")

    try:
        if mode == "auto":
            print("覆盖率自动过滤中...\n")
            print("[1/3] 统计分布自动选择过滤条件...")
            raw, parsed, next_issue = ai.analyze_and_filter_auto(data, n_recent)
        else:
            if not check_api_key():
                return
            print("AI分析 + 自动过滤中...\n")
            print("[1/3] AI生成过滤条件...")
            raw, parsed, next_issue = ai.analyze_and_filter(data, n_recent)
        filters = parsed["filters"]
        print(f"[1/3] 完成 → {next_issue}期")
        print(f"      {parsed['analysis']}")

        print("\n过滤条件:")
        for k, v in filters.items():
            if v:
                print(f"  {k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v}")

        print("\n[2/3] 执行过滤...")
        prev = [last["d1"], last["d2"], last["d3"]]
        missing_data = st.calc_missing_values(data)
        numbers, flog = fe.apply_filters(filters, prev, missing_data=missing_data)
        for line in flog:
            print(f"  {line}")

        count = len(numbers)

        # 出手判断
        import auto_select
        max_notes = getattr(auto_select, "MAX_BET_NOTES", 150)
        if count == 0:
            print("\n[!] 0注! 自动放宽...")
            for k in ["012路", "必含号码", "和尾", "质合比", "连号", "首尾差", "遗漏总值"]:
                if k in filters:
                    filters[k] = []
            numbers, flog = fe.apply_filters(filters, prev, missing_data=missing_data)
            count = len(numbers)
            for line in flog:
                print(f"  {line}")
            if count == 0:
                print("仍为0注，请用菜单2查看详细分析。")
                return
        elif count > max_notes:
            print(f"\n⚠️  本期过滤后{count}注 > {max_notes}注阈值")
            print(f"   建议: 本期跳过不下注 (过滤条件不够收敛)")
            print(f"   成本: {count*2}元 | 回测显示≤{max_notes}注时中1次成本最低")
            choice = input("   仍要保存? (y/N): ").strip().lower()
            if choice != "y":
                print("已跳过本期。")
                return

        print(f"\n[3/3] 保存...")
        gl_dir = get_gl_dir()
        seq = 1
        while os.path.exists(os.path.join(gl_dir, f"GL{next_issue}-{seq:02d}.txt")):
            seq += 1
        gl_name = f"GL{next_issue}-{seq:02d}.txt"
        gl_content = fe.format_gl_output(numbers, next_issue, seq)
        with open(os.path.join(gl_dir, gl_name), "w", encoding="gb18030") as f:
            f.write(gl_content)

        # 报告
        rpt_name = f"report_{next_issue}-{seq:02d}.txt"
        rpt_path = os.path.join(config.OUTPUT_DIR, rpt_name)
        with open(rpt_path, "w", encoding="utf-8") as f:
            f.write(f"FC3D_AI 报告 - {next_issue}期\n生成: {__import__('datetime').datetime.now()}\n")
            f.write(f"基于: {last['issue']}期 {last['d1']}{last['d2']}{last['d3']}\n")
            f.write(f"置信度: {parsed['confidence']}\n{'='*50}\n\n{parsed['analysis']}\n\n")
            f.write(json.dumps(filters, ensure_ascii=False, indent=2) + "\n\n")
            for i, n in enumerate(numbers):
                f.write(f"{i+1:3d}. {n[0]}{n[1]}{n[2]}\n")

        print("\n" + "=" * 55)
        print(f"  {next_issue}期 AI过滤结果: {count}注 (直选)")
        print("=" * 55)
        cols = 8
        for i in range(0, len(numbers), cols):
            row = numbers[i:i+cols]
            print("  " + " ".join(f"{n[0]}{n[1]}{n[2]}" for n in row))
        print("=" * 55)
        print(f"  GL文件: output/gl/{gl_name}")
        print(f"  报告:   output/{rpt_name}")

        if parsed["key_reasons"]:
            print("\n  理由:")
            for r in parsed["key_reasons"][:5]:
                print(f"    - {r}")
        if parsed["risk_notes"]:
            print("\n  风险:")
            for r in parsed["risk_notes"][:3]:
                print(f"    - {r}")

    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()


def func_predict(data):
    if not check_api_key():
        return
    n = input(f"参考期数 (默认{config.DEFAULT_RECENT_PERIODS}): ").strip()
    n_recent = int(n) if n.isdigit() else config.DEFAULT_RECENT_PERIODS
    print(f"\nAI分析中...")
    try:
        result = ai.analyze_next_period(data, min(n_recent, config.MAX_CONTEXT_PERIODS))
        print("\n" + "=" * 55)
        print(result)
        print("=" * 55)
        save = input("\n保存? (y/n): ").strip().lower()
        if save == "y":
            fp = os.path.join(config.OUTPUT_DIR, f"analysis_{data[-1]['issue']}.txt")
            with open(fp, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"已保存: {fp}")
    except Exception as e:
        print(f"[错误] {e}")


def func_review(data):
    if not check_api_key():
        return
    gl_files = dm.load_gl_files()
    if not gl_files:
        print("未找到GL文件")
        return
    print(f"\n最近5个GL文件:")
    for gl in gl_files[-5:]:
        print(f"  {gl['filename']}: {gl.get('issue', '?')}期 {gl['count']}注")
    c = input("\n文件名 (回车=最新): ").strip()
    sel = gl_files[-1]
    if c:
        for gl in gl_files:
            if c in gl["filename"]:
                sel = gl
                break
    print(f"\n复盘 {sel['filename']}...")
    try:
        result = ai.review_filter_result(data, sel)
        print("\n" + result)
    except Exception as e:
        print(f"[错误] {e}")


def func_batch_review(data):
    if not check_api_key():
        return
    gl_files = dm.load_gl_files()
    if not gl_files:
        print("未找到GL文件")
        return
    n = input(f"复盘几期? (默认全部{len(gl_files)}): ").strip()
    mx = int(n) if n.isdigit() else len(gl_files)
    print(f"\n批量复盘中...")
    try:
        result = ai.batch_review(data, gl_files, mx)
        print(f"\n{result['summary']}\n")
        print(f"{'期号':>9} {'文件':>18} {'注数':>5} {'开奖':>5} {'命中':>4}")
        print("-" * 50)
        for r in result["results"]:
            print(f"{r['期号']:>9} {r['文件']:>18} {r['注数']:>5} {r['开奖号码']:>5} {r['命中']:>4}")
        print("\n" + result["ai_analysis"])
    except Exception as e:
        print(f"[错误] {e}")


def func_chat(data):
    if not check_api_key():
        return
    print("\n对话模式 (输入q退出)")
    while True:
        q = input("你: ").strip()
        if q.lower() == "q":
            break
        if q:
            print("分析中...")
            try:
                print(f"\nAI: {ai.chat_analysis(data, q)}\n")
            except Exception as e:
                print(f"[错误] {e}")


def func_setup_schedule():
    """安装/卸载 Windows 计划任务"""
    task_name = "FC3D_AI_Daily"
    python_path = sys.executable
    script_path = os.path.join(config.BASE_DIR, "scheduler.py")

    print(f"\nWindows计划任务管理 (任务名: {task_name})")
    print(f"  执行时间: 每天 {config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d}")
    print(f"  执行命令: {python_path} {script_path} --now")
    print()
    print("  1 - 安装计划任务")
    print("  2 - 卸载计划任务")
    print("  3 - 查看任务状态")
    print("  0 - 返回")

    c = input("选择: ").strip()
    if c == "1":
        cmd = (
            f'schtasks /Create /TN "{task_name}" /TR '
            f'"\"{python_path}\" \"{script_path}\" --now" '
            f'/SC DAILY /ST {config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d} '
            f'/F /RL HIGHEST'
        )
        print(f"\n执行: {cmd}")
        ret = os.system(cmd)
        if ret == 0:
            print("\n计划任务已安装! 每天22:00自动执行。")
        else:
            print("\n安装失败，请尝试以管理员身份运行。")

    elif c == "2":
        cmd = f'schtasks /Delete /TN "{task_name}" /F'
        ret = os.system(cmd)
        if ret == 0:
            print("计划任务已卸载。")
        else:
            print("卸载失败。")

    elif c == "3":
        os.system(f'schtasks /Query /TN "{task_name}" /V /FO LIST')


def func_settings():
    """设置"""
    print(f"\n当前配置:")
    print(f"  API: {config.API_PROVIDER}")
    if config.API_PROVIDER == "poe":
        k = config.POE_API_KEY
        print(f"  Key: {k[:12]}...{k[-4:]}" if k else "  Key: 未设置")
        print(f"  模型: {config.POE_MODEL}")
    else:
        k = config.ANTHROPIC_API_KEY
        print(f"  Key: {k[:8]}...{k[-4:]}" if k else "  Key: 未设置")
        print(f"  模型: {config.ANTHROPIC_MODEL}")
    print(f"  定时: 每天 {config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d}")

    print("\n  1-切换Poe  2-切换Anthropic  3-改Poe Key  4-改Anthropic Key  0-返回")
    c = input("选择: ").strip()
    cfg_path = os.path.join(config.BASE_DIR, "config.py")

    def replace_in_config(old, new):
        with open(cfg_path, "r", encoding="utf-8") as f:
            txt = f.read()
        txt = txt.replace(old, new)
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(txt)

    if c == "1":
        replace_in_config(f'API_PROVIDER = "{config.API_PROVIDER}"', 'API_PROVIDER = "poe"')
        config.API_PROVIDER = "poe"
        print("已切换到 Poe!")
    elif c == "2":
        replace_in_config(f'API_PROVIDER = "{config.API_PROVIDER}"', 'API_PROVIDER = "anthropic"')
        config.API_PROVIDER = "anthropic"
        print("已切换到 Anthropic!")
    elif c == "3":
        nk = input("Poe Key: ").strip()
        if nk:
            replace_in_config(f'POE_API_KEY = "{config.POE_API_KEY}"', f'POE_API_KEY = "{nk}"')
            config.POE_API_KEY = nk
            print("已保存!")
    elif c == "4":
        nk = input("Anthropic Key: ").strip()
        if nk:
            replace_in_config(f'ANTHROPIC_API_KEY = "{config.ANTHROPIC_API_KEY}"', f'ANTHROPIC_API_KEY = "{nk}"')
            config.ANTHROPIC_API_KEY = nk
            print("已保存!")


def main():
    print_banner()
    print("\n加载数据...")
    data = dm.load_or_download()
    if not data:
        print("[!] 无数据 → 选7下载或8手动录入")

    while True:
        print_menu()
        c = input("选择: ").strip().lower()

        if c == "1":
            data and func_auto_filter(data) or print("先加载数据")
        elif c == "s":
            data and func_semi_auto_filter(data) or print("先加载数据")
        elif c == "2":
            data and func_predict(data) or print("先加载数据")
        elif c == "3":
            data and func_review(data) or print("先加载数据")
        elif c == "4":
            data and func_batch_review(data) or print("先加载数据")
        elif c == "5":
            data and func_chat(data) or print("先加载数据")
        elif c == "6":
            data and show_stats(data) or print("无数据")
        elif c == "7":
            data, _ = dm.update_data(data)
        elif c == "8":
            data = dm.manual_input_data()
        elif c == "9":
            func_settings()
        elif c == "b":
            if data:
                func_backtest(data)
            else:
                print("先加载数据")
        elif c == "d":
            print("\n立即执行每日任务...")
            scheduler.run_daily_task()
            data = dm.load_csv()  # 刷新数据
        elif c == "t":
            func_setup_schedule()
        elif c == "0":
            print("\n再见!")
            break
        else:
            print("无效选择")


if __name__ == "__main__":
    main()
