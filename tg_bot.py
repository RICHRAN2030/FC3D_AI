"""
FC3D_AI Telegram Bot
所有功能通过TG机器人操作，定时任务结果自动推送
"""
import sys
import os
import json
import asyncio
import logging
from datetime import datetime, time as dtime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import data_manager as dm
import ai_engine as ai
import filter_engine as fe
import stats as st

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters,
)

# 确保目录 (必须在logging之前)
os.makedirs(config.LOG_DIR, exist_ok=True)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(config.OUTPUT_DIR, "gl"), exist_ok=True)

# 日志
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(config.LOG_DIR, "tg_bot.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("FC3D_Bot")


# ============================================================
# 工具函数
# ============================================================

def is_admin(update: Update) -> bool:
    return update.effective_user.id == config.TG_ADMIN_ID


async def run_with_typing(chat_id, bot, coro):
    """
    执行耗时任务的同时，持续发送 'typing...' 状态给用户。
    Telegram typing状态只维持5秒，所以每4秒刷新一次。
    coro: 要执行的协程(如 asyncio.to_thread(...))
    """
    stop_event = asyncio.Event()

    async def keep_typing():
        while not stop_event.is_set():
            try:
                await bot.send_chat_action(chat_id=chat_id, action="typing")
            except Exception:
                pass
            # 等4秒或被停止
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=4)
                break
            except asyncio.TimeoutError:
                pass

    typing_task = asyncio.create_task(keep_typing())
    try:
        result = await coro
        return result
    finally:
        stop_event.set()
        await typing_task


async def send_long_message(context, chat_id, text, max_len=4000):
    """TG单条消息限制4096字符，超长自动分段发送"""
    if len(text) <= max_len:
        await context.bot.send_message(chat_id=chat_id, text=text)
        return
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        cut = text[:max_len].rfind("\n")
        if cut < max_len // 2:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    for i, part in enumerate(parts):
        await context.bot.send_message(chat_id=chat_id, text=part)


def get_gl_dir():
    d = os.path.join(config.OUTPUT_DIR, "gl")
    os.makedirs(d, exist_ok=True)
    return d


# ============================================================
# /start - 欢迎
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("无权限")
        return
    await update.message.reply_text(
        "🎯 FC3D_AI 福彩3D智能分析\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 命令列表:\n"
        "/filter - ★ 一键AI过滤出号\n"
        "/report - AI详细分析报告\n"
        "/review - 复盘最新过滤结果\n"
        "/stats - 数据统计总览\n"
        "/update - 更新开奖数据\n"
        "/ask 问题 - 自由提问\n"
        "/daily - 立即执行每日任务\n"
        "/help - 帮助\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⏰ 每天 {config.SCHEDULE_HOUR}:{config.SCHEDULE_MINUTE:02d} 自动推送"
    )


# ============================================================
# /filter - 一键AI过滤出号
# ============================================================

async def cmd_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    msg = await update.message.reply_text("🔄 正在AI分析 + 自动过滤，请稍候...")

    try:
        data = dm.load_or_download()
        last = data[-1]

        # AI分析 (线程池+typing提示)
        raw, parsed, next_issue = await run_with_typing(
            update.effective_chat.id, context.bot,
            asyncio.to_thread(
                ai.analyze_and_filter_auto if getattr(config, 'FILTER_MODE', 'auto') == 'auto' else ai.analyze_and_filter,
                data, config.DEFAULT_RECENT_PERIODS
            )
        )
        filters_dict = parsed["filters"]

        # 执行过滤
        prev = [last["d1"], last["d2"], last["d3"]]
        missing_data = st.calc_missing_values(data)
        numbers, flog = fe.apply_filters(filters_dict, prev, missing_data=missing_data)

        # 0注则放宽
        if len(numbers) == 0:
            for k in ["012路", "必含号码", "和尾", "质合比", "连号", "首尾差", "遗漏总值"]:
                if k in filters_dict:
                    filters_dict[k] = []
            numbers, flog = fe.apply_filters(filters_dict, prev, missing_data=missing_data)

        count = len(numbers)

        # 出手判断
        import auto_select
        max_notes = getattr(auto_select, "MAX_BET_NOTES", 150)
        if count > max_notes:
            await msg.edit_text(
                f"⏭️ {next_issue}期 建议跳过\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"过滤后{count}注 > {max_notes}注阈值\n"
                f"条件不够收敛，成本过高({count*2}元)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💡 等条件更收敛时再出手"
            )
            logger.info(f"{next_issue}期跳过: {count}注>{max_notes}")
            return

        # 保存GL
        gl_dir = get_gl_dir()
        seq = 1
        while os.path.exists(os.path.join(gl_dir, f"GL{next_issue}-{seq:02d}.txt")):
            seq += 1
        gl_name = f"GL{next_issue}-{seq:02d}.txt"
        gl_content = fe.format_gl_output(numbers, next_issue, seq)
        with open(os.path.join(gl_dir, gl_name), "w", encoding="gb18030") as f:
            f.write(gl_content)

        # 构建回复消息
        # 号码分行显示
        num_lines = []
        cols = 8
        for i in range(0, len(numbers), cols):
            row = numbers[i:i+cols]
            num_lines.append(" ".join(f"{n[0]}{n[1]}{n[2]}" for n in row))

        # 过滤过程
        filter_steps = "\n".join(f"  {l}" for l in flog)

        # 核心理由
        reasons = ""
        if parsed.get("key_reasons"):
            reasons = "\n📋 核心理由:\n" + "\n".join(f"• {r}" for r in parsed["key_reasons"][:5])

        # 风险
        risks = ""
        if parsed.get("risk_notes"):
            risks = "\n⚠️ 风险提示:\n" + "\n".join(f"• {r}" for r in parsed["risk_notes"][:3])

        text = (
            f"🎯 {next_issue}期 AI过滤结果\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 基于: {last['issue']}期 {last['d1']}{last['d2']}{last['d3']}\n"
            f"🤖 AI: {parsed.get('analysis', '')}\n"
            f"📈 置信度: {parsed.get('confidence', '中')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔢 过滤结果: {count}注 (直选)\n\n"
            f"{chr(10).join(num_lines)}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 过滤过程:\n{filter_steps}\n"
            f"{reasons}"
            f"{risks}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💾 已保存: {gl_name}"
        )

        await msg.edit_text(text)
        logger.info(f"过滤完成: {next_issue}期 {count}注")

    except Exception as e:
        await msg.edit_text(f"❌ 过滤失败: {e}")
        logger.error(f"过滤失败: {e}", exc_info=True)


# ============================================================
# /report - AI详细分析报告
# ============================================================

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    msg = await update.message.reply_text("🔄 AI正在生成详细分析报告...")

    try:
        data = dm.load_or_download()
        result = await run_with_typing(
            update.effective_chat.id, context.bot,
            asyncio.to_thread(ai.analyze_next_period, data, config.DEFAULT_RECENT_PERIODS)
        )
        await msg.edit_text("📊 AI分析报告\n━━━━━━━━━━━━━━━━━━")
        await send_long_message(context, update.effective_chat.id, result)
        logger.info("分析报告已发送")
    except Exception as e:
        await msg.edit_text(f"❌ 分析失败: {e}")


# ============================================================
# /review - 复盘最新过滤结果
# ============================================================

async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    msg = await update.message.reply_text("🔄 正在复盘...")

    try:
        data = dm.load_or_download()
        gl_files = dm.load_gl_files()

        if not gl_files:
            await msg.edit_text("❌ 未找到GL过滤文件")
            return

        sel = gl_files[-1]

        # 检查命中
        issue = sel.get("issue", "")
        actual = None
        for d in data:
            if d["issue"] == issue:
                actual = d
                break

        hit_info = ""
        if actual:
            actual_tuple = (actual["d1"], actual["d2"], actual["d3"])
            if actual_tuple in sel["numbers"]:
                hit_info = f"\n🎉 命中! 开奖 {actual['d1']}{actual['d2']}{actual['d3']} 在过滤结果中!"
            else:
                hit_info = f"\n❌ 未命中 开奖 {actual['d1']}{actual['d2']}{actual['d3']}"

        # AI复盘 (线程池+typing)
        result = await run_with_typing(
            update.effective_chat.id, context.bot,
            asyncio.to_thread(ai.review_filter_result, data, sel)
        )

        text = (
            f"📋 复盘: {sel['filename']}\n"
            f"期号: {issue}期 | {sel['count']}注"
            f"{hit_info}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        await msg.edit_text(text)
        await send_long_message(context, update.effective_chat.id, result)

    except Exception as e:
        await msg.edit_text(f"❌ 复盘失败: {e}")


# ============================================================
# /stats - 数据统计
# ============================================================

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    data = dm.load_or_download()
    if not data:
        await update.message.reply_text("❌ 无数据")
        return

    # 最近10期
    lines = [f"📊 数据: {len(data)}期 ({data[0]['issue']}~{data[-1]['issue']})\n"]
    lines.append("最近10期:")
    lines.append(f"{'期号':>8} 号码 和值 跨度 AC 奇偶  大小")
    lines.append("─" * 40)
    for d in data[-10:]:
        s = st.calc_sum(d["d1"], d["d2"], d["d3"])
        sp = st.calc_span(d["d1"], d["d2"], d["d3"])
        ac = st.calc_ac(d["d1"], d["d2"], d["d3"])
        oe = st.calc_odd_even(d["d1"], d["d2"], d["d3"])
        bs = st.calc_big_small(d["d1"], d["d2"], d["d3"])
        lines.append(f"{d['issue']} {d['d1']}{d['d2']}{d['d3']}  {s:>2}   {sp}   {ac}  {oe} {bs}")

    # 遗漏值
    missing = st.calc_missing_values(data)
    lines.append("\n🔢 遗漏值:")
    lines.append(f"     0   1   2   3   4   5   6   7   8   9")
    for pos in ["百位", "十位", "个位"]:
        vals = " ".join(f"{missing[pos].get(i,0):>3}" for i in range(10))
        lines.append(f"{pos} {vals}")

    # 热温冷
    hc = st.calc_hot_cold(data, 30)
    lines.append("\n🌡️ 热温冷 (近30期):")
    for pos in ["百位", "十位", "个位"]:
        lines.append(f"  {pos}: 热{hc[pos]['热']} 温{hc[pos]['温']} 冷{hc[pos]['冷']}")

    await update.message.reply_text("\n".join(lines))


# ============================================================
# /update - 更新数据
# ============================================================

async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    msg = await update.message.reply_text("🔄 正在更新开奖数据...")
    try:
        data, added = dm.update_data()
        latest = data[-1] if data else None
        text = f"✅ 数据更新完成\n总: {len(data)}期 | 新增: {added}期"
        if latest:
            text += f"\n最新: {latest['issue']}期 {latest['d1']}{latest['d2']}{latest['d3']}"
        await msg.edit_text(text)
    except Exception as e:
        await msg.edit_text(f"❌ 更新失败: {e}")


# ============================================================
# /ask - 自由提问
# ============================================================

async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text("用法: /ask 你的问题\n例如: /ask 最近和值走势怎么样")
        return

    msg = await update.message.reply_text("🤔 AI分析中...")
    try:
        data = dm.load_or_download()
        result = await run_with_typing(
            update.effective_chat.id, context.bot,
            asyncio.to_thread(ai.chat_analysis, data, question)
        )
        await msg.edit_text(f"💬 {question}\n━━━━━━━━━━━━━━━━━━")
        await send_long_message(context, update.effective_chat.id, result)
    except Exception as e:
        await msg.edit_text(f"❌ 失败: {e}")


# ============================================================
# /daily - 手动触发每日任务
# ============================================================

async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    msg = await update.message.reply_text("🔄 正在执行每日任务 (更新+复盘+出号)...")
    try:
        result = await run_daily_job(context)
        await msg.edit_text("✅ 每日任务完成! 结果已发送")
    except Exception as e:
        await msg.edit_text(f"❌ 每日任务失败: {e}")
        logger.error(f"每日任务失败: {e}", exc_info=True)


# ============================================================
# /help
# ============================================================

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 FC3D_AI 命令说明\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "/filter - 一键AI过滤出号 (生成GL文件)\n"
        "/report - AI详细分析报告 (趋势/胆码/推荐)\n"
        "/review - 复盘最近一次过滤结果\n"
        "/stats  - 遗漏值/热冷号/近10期统计\n"
        "/update - 从中彩网更新最新开奖数据\n"
        "/ask 问题 - 自由提问AI分析\n"
        "/daily  - 手动触发每日任务\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⏰ 自动任务: 每天{config.SCHEDULE_HOUR}:{config.SCHEDULE_MINUTE:02d}\n"
        "   → 获取开奖 → 复盘 → 出明日号码\n"
        "   → 结果自动推送到这里"
    )


# ============================================================
# 普通消息 → 当作提问
# ============================================================

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    text = update.message.text.strip()
    if not text:
        return
    # 把普通消息当作提问
    context.args = text.split()
    await cmd_ask(update, context)


# ============================================================
# 每日定时任务 (TG版)
# ============================================================

async def run_daily_job(context: ContextTypes.DEFAULT_TYPE):
    """每日自动任务: 更新数据 → 复盘 → 生成明日方案 → 推送"""
    chat_id = config.TG_ADMIN_ID
    logger.info("每日定时任务开始")

    # ===== 步骤1: 更新数据 =====
    await context.bot.send_message(chat_id=chat_id, text="⏰ 每日定时任务启动\n━━━━━━━━━━━━━━━━━━")

    data, added = await asyncio.to_thread(dm.update_data)
    if not data:
        await context.bot.send_message(chat_id=chat_id, text="❌ 无法获取数据")
        return

    latest = data[-1]
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"📥 步骤1: 数据更新\n"
            f"总: {len(data)}期 | 新增: {added}期\n"
            f"最新: {latest['issue']}期 → {latest['d1']}{latest['d2']}{latest['d3']}"
        ),
    )

    # ===== 步骤2: 复盘今天 =====
    gl_files = dm.load_gl_files()
    today_issue = latest["issue"]
    today_gls = [g for g in gl_files if g.get("issue") == today_issue]

    if today_gls:
        actual = (latest["d1"], latest["d2"], latest["d3"])
        review_text = f"📋 步骤2: 复盘 {today_issue}期\n"
        review_text += f"开奖号码: {actual[0]}{actual[1]}{actual[2]}\n━━━━━━━━━━━━━━━━━━\n"

        any_hit = False
        for gl in today_gls:
            hit = actual in gl["numbers"]
            if hit:
                any_hit = True
            status = "🎉 命中!" if hit else "❌ 未命中"
            review_text += f"{gl['filename']}: {gl['count']}注 → {status}\n"

        await context.bot.send_message(chat_id=chat_id, text=review_text)

        # AI复盘分析
        try:
            ai_review = await run_with_typing(
                chat_id, context.bot,
                asyncio.to_thread(ai.review_filter_result, data, today_gls[0])
            )
            await context.bot.send_message(chat_id=chat_id, text="🤖 AI复盘分析:")
            await send_long_message(context, chat_id, ai_review)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"AI复盘失败: {e}")
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📋 步骤2: 无{today_issue}期的GL文件，跳过复盘",
        )

    # ===== 步骤3: 生成明日方案 =====
    await context.bot.send_message(chat_id=chat_id, text="🔄 步骤3: 生成下一期AI过滤方案...")

    try:
        raw, parsed, next_issue = await run_with_typing(
            chat_id, context.bot,
            asyncio.to_thread(
                ai.analyze_and_filter_auto if getattr(config, 'FILTER_MODE', 'auto') == 'auto' else ai.analyze_and_filter,
                data, config.DEFAULT_RECENT_PERIODS
            )
        )
        filters_dict = parsed["filters"]
        prev = [latest["d1"], latest["d2"], latest["d3"]]
        missing_data = st.calc_missing_values(data)
        numbers, flog = fe.apply_filters(filters_dict, prev, missing_data=missing_data)

        if len(numbers) == 0:
            for k in ["012路", "必含号码", "和尾", "质合比", "连号", "首尾差", "遗漏总值"]:
                if k in filters_dict:
                    filters_dict[k] = []
            numbers, flog = fe.apply_filters(filters_dict, prev, missing_data=missing_data)

        count = len(numbers)

        # 保存GL
        gl_dir = get_gl_dir()
        seq = 1
        while os.path.exists(os.path.join(gl_dir, f"GL{next_issue}-{seq:02d}.txt")):
            seq += 1
        gl_name = f"GL{next_issue}-{seq:02d}.txt"
        gl_content = fe.format_gl_output(numbers, next_issue, seq)
        with open(os.path.join(gl_dir, gl_name), "w", encoding="gb18030") as f:
            f.write(gl_content)

        # 号码显示
        num_lines = []
        cols = 8
        for i in range(0, len(numbers), cols):
            row = numbers[i:i+cols]
            num_lines.append(" ".join(f"{n[0]}{n[1]}{n[2]}" for n in row))

        filter_steps = "\n".join(f"  {l}" for l in flog)

        reasons = ""
        if parsed.get("key_reasons"):
            reasons = "\n📋 理由:\n" + "\n".join(f"• {r}" for r in parsed["key_reasons"][:5])

        risks = ""
        if parsed.get("risk_notes"):
            risks = "\n⚠️ 风险:\n" + "\n".join(f"• {r}" for r in parsed["risk_notes"][:3])

        result_text = (
            f"🎯 {next_issue}期 AI过滤结果\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 {parsed.get('analysis', '')}\n"
            f"📈 置信度: {parsed.get('confidence', '中')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔢 {count}注 (直选)\n\n"
            f"{chr(10).join(num_lines)}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 过程:\n{filter_steps}\n"
            f"{reasons}{risks}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💾 {gl_name}"
        )
        await send_long_message(context, chat_id, result_text)
        logger.info(f"每日任务: {next_issue}期 {count}注")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 生成失败: {e}")
        logger.error(f"生成失败: {e}", exc_info=True)

    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ 每日任务全部完成!",
    )


async def scheduled_daily_callback(context: ContextTypes.DEFAULT_TYPE):
    """被 JobQueue 调用的定时回调"""
    logger.info("定时触发每日任务")
    try:
        await run_daily_job(context)
    except Exception as e:
        logger.error(f"定时任务异常: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=config.TG_ADMIN_ID,
                text=f"❌ 定时任务异常: {e}",
            )
        except:
            pass


# ============================================================
# 启动
# ============================================================

def main():
    print("=" * 50)
    print("  FC3D_AI Telegram Bot 启动中...")
    print(f"  定时任务: 每天 {config.SCHEDULE_HOUR}:{config.SCHEDULE_MINUTE:02d}")
    print(f"  管理员ID: {config.TG_ADMIN_ID}")
    print("=" * 50)

    app = Application.builder().token(config.TG_BOT_TOKEN).build()

    # 注册命令
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("filter", cmd_filter))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("review", cmd_review))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("update", cmd_update))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("daily", cmd_daily))

    # 普通消息当提问
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    # 注册定时任务: 每天22:00
    job_queue = app.job_queue
    target_time = dtime(
        hour=config.SCHEDULE_HOUR,
        minute=config.SCHEDULE_MINUTE,
        second=0,
    )
    job_queue.run_daily(
        scheduled_daily_callback,
        time=target_time,
        name="daily_task",
    )
    print(f"  定时任务已注册: 每天 {target_time}")

    # 启动通知
    async def post_init(application):
        await application.bot.send_message(
            chat_id=config.TG_ADMIN_ID,
            text=(
                "🟢 FC3D_AI Bot 已上线!\n"
                f"⏰ 定时任务: 每天{config.SCHEDULE_HOUR}:{config.SCHEDULE_MINUTE:02d}\n"
                "发送 /help 查看命令"
            ),
        )
        # 设置命令菜单
        await application.bot.set_my_commands([
            BotCommand("filter", "★ 一键AI过滤出号"),
            BotCommand("report", "AI详细分析报告"),
            BotCommand("review", "复盘最新过滤结果"),
            BotCommand("stats", "数据统计总览"),
            BotCommand("update", "更新开奖数据"),
            BotCommand("ask", "自由提问 (后接问题)"),
            BotCommand("daily", "立即执行每日任务"),
            BotCommand("help", "帮助"),
        ])

    app.post_init = post_init

    print("\n  Bot启动! 按 Ctrl+C 停止\n")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
