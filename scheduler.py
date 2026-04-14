"""
定时任务 - 每天22:00自动执行:
1. 获取当天开奖结果
2. 更新本地数据
3. 复盘今天的AI过滤结果(如果有)
4. 自动生成明天的AI过滤方案
5. 记录日志
"""
import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import data_manager as dm
import ai_engine as ai
import filter_engine as fe
import stats as st


def log(msg, log_file=None):
    """写日志到控制台和文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def get_log_path():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(config.LOG_DIR, f"daily_{today}.log")


def get_gl_dir():
    gl_dir = os.path.join(config.OUTPUT_DIR, "gl")
    os.makedirs(gl_dir, exist_ok=True)
    return gl_dir


def step1_fetch_and_update(logf):
    """步骤1: 获取最新开奖 + 更新数据"""
    log("=" * 50, logf)
    log("步骤1: 获取最新开奖结果", logf)

    # 先获取最新一期
    latest = dm.fetch_today_result()
    if latest:
        log(f"最新开奖: {latest['issue']}期 → {latest['d1']}{latest['d2']}{latest['d3']} ({latest.get('date','')})", logf)
    else:
        log("未获取到开奖结果(可能尚未开奖或网络问题)", logf)

    # 增量更新全部数据
    data, added_count = dm.update_data()
    log(f"数据更新: 总{len(data)}期, 新增{added_count}期", logf)

    return data, latest


def step2_review_today(data, today_result, logf):
    """步骤2: 复盘今天的AI过滤结果"""
    log("=" * 50, logf)
    log("步骤2: 复盘今日过滤结果", logf)

    if not today_result:
        log("无开奖结果，跳过复盘", logf)
        return None

    issue = today_result["issue"]
    actual = (today_result["d1"], today_result["d2"], today_result["d3"])
    log(f"复盘期号: {issue}  开奖: {actual[0]}{actual[1]}{actual[2]}", logf)

    # 查找该期的GL文件
    gl_dir = get_gl_dir()
    gl_files = []
    for f in sorted(os.listdir(gl_dir)):
        if f.startswith(f"GL{issue}") and f.endswith(".txt"):
            gl_files.append(f)

    if not gl_files:
        log(f"未找到{issue}期的GL过滤文件，跳过复盘", logf)
        return None

    review_results = []
    for gl_name in gl_files:
        gl_path = os.path.join(gl_dir, gl_name)
        parsed = dm.parse_gl_file(gl_path)

        hit = actual in parsed["numbers"]
        status = "命中!" if hit else "未命中"
        log(f"  {gl_name}: {parsed['count']}注 → {status}", logf)

        review_results.append({
            "filename": gl_name,
            "count": parsed["count"],
            "hit": hit,
            "numbers": parsed["numbers"],
        })

    # 调用AI做详细复盘分析
    any_hit = any(r["hit"] for r in review_results)
    total_files = len(review_results)
    hit_files = sum(1 for r in review_results if r["hit"])

    log(f"  汇总: {total_files}个方案, 命中{hit_files}个", logf)

    # 用AI分析最主要的那个方案
    main_gl = review_results[0]
    try:
        gl_data = dm.parse_gl_file(os.path.join(gl_dir, main_gl["filename"]))
        gl_data["filename"] = main_gl["filename"]
        ai_review = ai.review_filter_result(data, gl_data)
        log(f"\nAI复盘分析:\n{ai_review}", logf)
    except Exception as e:
        log(f"AI复盘失败: {e}", logf)
        ai_review = None

    return {
        "issue": issue,
        "actual": actual,
        "results": review_results,
        "any_hit": any_hit,
        "ai_review": ai_review,
    }


def step3_generate_tomorrow(data, logf):
    """步骤3: 生成明天(下一期)的AI过滤方案"""
    log("=" * 50, logf)
    log("步骤3: 生成下一期AI过滤方案", logf)

    try:
        filter_func = ai.analyze_and_filter_auto if getattr(config, 'FILTER_MODE', 'auto') == 'auto' else ai.analyze_and_filter
        raw, parsed, next_issue = filter_func(data, config.DEFAULT_RECENT_PERIODS)
        filters = parsed["filters"]

        log(f"目标期号: {next_issue}", logf)
        log(f"AI分析: {parsed['analysis']}", logf)
        log(f"置信度: {parsed['confidence']}", logf)

        # 执行过滤
        last = data[-1]
        prev = [last["d1"], last["d2"], last["d3"]]
        missing_data = st.calc_missing_values(data)
        numbers, filter_log = fe.apply_filters(filters, prev, missing_data=missing_data)

        for line in filter_log:
            log(f"  {line}", logf)

        result_count = len(numbers)
        log(f"过滤结果: {result_count}注", logf)

        if result_count == 0:
            log("结果为0注! 放宽条件重试...", logf)
            for key in ["012路", "必含号码", "和尾", "质合比", "连号", "首尾差", "遗漏总值"]:
                if key in filters:
                    filters[key] = []
            numbers, filter_log = fe.apply_filters(filters, prev, missing_data=missing_data)
            result_count = len(numbers)
            log(f"放宽后: {result_count}注", logf)

        if result_count > 0:
            # 保存GL文件
            gl_dir = get_gl_dir()
            seq = 1
            while os.path.exists(os.path.join(gl_dir, f"GL{next_issue}-{seq:02d}.txt")):
                seq += 1
            gl_filename = f"GL{next_issue}-{seq:02d}.txt"
            gl_content = fe.format_gl_output(numbers, next_issue, seq)
            with open(os.path.join(gl_dir, gl_filename), "w", encoding="gb18030") as f:
                f.write(gl_content)
            log(f"已保存: gl/{gl_filename} ({result_count}注)", logf)

            # 保存分析报告
            report_name = f"report_{next_issue}-{seq:02d}.txt"
            report_path = os.path.join(config.OUTPUT_DIR, report_name)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"FC3D_AI 自动分析报告 - {next_issue}期\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"基于: {last['issue']}期 ({last['d1']}{last['d2']}{last['d3']})\n")
                f.write(f"置信度: {parsed['confidence']}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"分析: {parsed['analysis']}\n\n")
                if parsed["key_reasons"]:
                    f.write("核心理由:\n")
                    for r in parsed["key_reasons"]:
                        f.write(f"  {r}\n")
                    f.write("\n")
                if parsed["risk_notes"]:
                    f.write("风险提示:\n")
                    for r in parsed["risk_notes"]:
                        f.write(f"  {r}\n")
                    f.write("\n")
                f.write("过滤条件:\n")
                f.write(json.dumps(filters, ensure_ascii=False, indent=2))
                f.write(f"\n\n过滤过程:\n")
                for line in filter_log:
                    f.write(f"  {line}\n")
                f.write(f"\n最终: {result_count}注\n\n号码:\n")
                for i, n in enumerate(numbers):
                    f.write(f"  {i+1:3d}. {n[0]}{n[1]}{n[2]}\n")
            log(f"报告: {report_name}", logf)

            # 显示号码
            log(f"\n{next_issue}期推荐号码 ({result_count}注):", logf)
            cols = 8
            for i in range(0, len(numbers), cols):
                row = numbers[i:i+cols]
                log("  " + " ".join(f"{n[0]}{n[1]}{n[2]}" for n in row), logf)

        return {"issue": next_issue, "count": result_count, "filters": filters}

    except Exception as e:
        log(f"生成失败: {e}", logf)
        import traceback
        traceback.print_exc()
        return None


def run_daily_task():
    """执行每日定时任务的完整流程"""
    logf = get_log_path()
    log("", logf)
    log("=" * 50, logf)
    log("FC3D_AI 每日定时任务启动", logf)
    log("=" * 50, logf)

    try:
        # 步骤1: 获取开奖 + 更新数据
        data, today_result = step1_fetch_and_update(logf)
        if not data:
            log("无数据，任务终止", logf)
            return

        # 步骤2: 复盘今日
        review = step2_review_today(data, today_result, logf)

        # 步骤3: 生成明天方案
        tomorrow = step3_generate_tomorrow(data, logf)

        # 汇总
        log("=" * 50, logf)
        log("每日任务完成!", logf)
        if today_result:
            issue = today_result["issue"]
            log(f"  今日开奖: {issue}期 {today_result['d1']}{today_result['d2']}{today_result['d3']}", logf)
            if review and review["any_hit"]:
                log(f"  复盘结果: 命中!", logf)
            elif review:
                log(f"  复盘结果: 未命中", logf)
        if tomorrow:
            log(f"  明日方案: {tomorrow['issue']}期 {tomorrow['count']}注 已生成", logf)
        log("=" * 50, logf)

        # 步骤4: 推送TG
        send_tg_summary(data, today_result, review, tomorrow, logf)

    except Exception as e:
        log(f"任务异常: {e}", logf)
        import traceback
        traceback.print_exc()
        # 异常也尝试推送
        try:
            send_tg_message(f"❌ FC3D_AI每日任务异常: {e}")
        except:
            pass


def send_tg_message(text):
    """直接HTTP发TG消息（不需要tg_bot.py运行）"""
    token = config.TG_BOT_TOKEN
    chat_id = config.TG_ADMIN_ID
    if not token or not chat_id:
        return
    import urllib.request
    import urllib.parse
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # 分段发送
    while text:
        chunk = text[:4000]
        text = text[4000:]
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": chunk,
        }).encode()
        try:
            urllib.request.urlopen(url, data, timeout=30)
        except Exception:
            pass


def send_tg_summary(data, today_result, review, tomorrow, logf):
    """每日任务完成后推送TG汇总"""
    token = config.TG_BOT_TOKEN
    chat_id = config.TG_ADMIN_ID
    if not token or not chat_id:
        log("TG未配置，跳过推送", logf)
        return

    lines = ["⏰ FC3D_AI 每日报告", "━━━━━━━━━━━━━━━━━━"]

    # 今日开奖
    if today_result:
        lines.append(f"📥 开奖: {today_result['issue']}期 → {today_result['d1']}{today_result['d2']}{today_result['d3']}")

    # 复盘
    if review:
        if review.get("any_hit"):
            lines.append("🎉 复盘: 命中!")
        else:
            lines.append("❌ 复盘: 未命中")
        for r in review.get("results", []):
            status = "🎉命中" if r["hit"] else "❌未中"
            lines.append(f"  {r['filename']}: {r['count']}注 {status}")

    # 明日方案
    if tomorrow:
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append(f"🎯 {tomorrow['issue']}期 过滤结果: {tomorrow['count']}注")
        lines.append(f"💰 成本: {tomorrow['count']*2}元")

        # 读GL文件获取号码
        gl_dir = get_gl_dir()
        gl_files = sorted([f for f in os.listdir(gl_dir) if f.startswith(f"GL{tomorrow['issue']}")])
        if gl_files:
            gl_path = os.path.join(gl_dir, gl_files[-1])
            try:
                with open(gl_path, "r", encoding="gb18030") as f:
                    gl_lines = f.read().strip().split("\n")
                nums = [l.strip() for l in gl_lines[1:] if l.strip()]
                # 分行显示
                cols = 10
                for i in range(0, len(nums), cols):
                    row = nums[i:i+cols]
                    lines.append(" ".join(row))
            except:
                pass

    lines.append("━━━━━━━━━━━━━━━━━━")

    msg = "\n".join(lines)
    send_tg_message(msg)
    log("已推送TG", logf)


def run_daemon():
    """守护进程模式: 持续运行，每天定时执行"""
    print(f"FC3D_AI 守护进程已启动")
    print(f"每天 {config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d} 自动执行")
    print(f"按 Ctrl+C 停止\n")

    while True:
        now = datetime.now()
        target = now.replace(hour=config.SCHEDULE_HOUR, minute=config.SCHEDULE_MINUTE, second=0, microsecond=0)

        # 如果今天的时间已过，等到明天
        if now >= target:
            from datetime import timedelta
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        hours = int(wait_seconds // 3600)
        mins = int((wait_seconds % 3600) // 60)
        print(f"[{now.strftime('%H:%M:%S')}] 下次执行: {target.strftime('%Y-%m-%d %H:%M')} (还有{hours}小时{mins}分钟)")

        try:
            time.sleep(wait_seconds)
            run_daily_task()
        except KeyboardInterrupt:
            print("\n守护进程已停止")
            break
        except Exception as e:
            print(f"执行出错: {e}")
            time.sleep(60)  # 出错后等1分钟再继续


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # 立即执行一次
        run_daily_task()
    elif len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # 守护进程模式
        run_daemon()
    else:
        print("用法:")
        print("  python scheduler.py --now      立即执行一次每日任务")
        print("  python scheduler.py --daemon   守护进程(持续运行,每天22:00执行)")
        print()
        print("也可通过 Windows 计划任务自动运行 (推荐)")
