# FC3D_AI - China Welfare Lottery 3D AI Prediction Tool

AI-powered analysis and filtering tool for China Welfare Lottery 3D (福彩3D), using Claude as the AI engine via Poe API.

## Features

- **AI Analysis Engine** — Claude Opus 4.6 (via Poe API, `output_effort: high`) for deep trend analysis
- **16 Filter Methods** — Sum, span, AC value, odd/even ratio, big/small ratio, 012 road, group type, position digits, repeat numbers, sum tail, prime/composite, consecutive, head-tail diff, must-contain, exclude
- **One-Click Filtering** — AI outputs structured JSON → filters applied automatically → GL file generated
- **Daily Scheduler** — Auto-runs at 22:00: fetch results → review past predictions → generate next-day selections
- **Telegram Bot** — Full-featured bot with all commands, scheduled push, typing indicator during AI processing
- **CLI Interface** — Interactive menu for local use
- **GL File Compatible** — Output files work with legacy 3DBZ.exe software (GB18030 encoding, direct selection mode)

## Quick Start

### 1. Install Dependencies

```bash
pip install openai httpx python-telegram-bot[job-queue] apscheduler
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required keys in `.env`:
- `POE_API_KEY` — Your Poe API key ([get one here](https://poe.com/api_key))
- `TG_BOT_TOKEN` — Your Telegram Bot token (from [@BotFather](https://t.me/BotFather))
- `TG_ADMIN_ID` — Your Telegram user ID

### 3. Run

```bash
# CLI mode
python main.py

# Telegram Bot
python tg_bot.py

# Daily scheduler (daemon)
python scheduler.py --daemon
```

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/filter` | One-click AI filter + number generation |
| `/report` | AI trend analysis report |
| `/review` | Review past predictions vs actual results |
| `/stats` | Statistical summary (hot/cold, missing values) |
| `/update` | Update lottery draw data |
| `/ask <question>` | Free-form AI Q&A |
| `/daily` | Trigger daily task manually |

Plain text messages are treated as AI questions.

## Project Structure

```
FC3D_AI/
├── config.py          # Configuration (reads secrets from .env)
├── ai_engine.py       # AI engine (Poe API / Anthropic API)
├── filter_engine.py   # 16 filter methods + GL file output
├── stats.py           # Statistical calculations
├── data_manager.py    # Data download/update from cwl.gov.cn
├── main.py            # CLI interactive menu
├── tg_bot.py          # Telegram bot
├── scheduler.py       # Daily scheduled task
├── .env.example       # Environment variable template
└── .env               # Your secrets (git-ignored)
```

## How It Works

```
Daily at 22:00 (auto or manual):
  1. Fetch today's draw result from cwl.gov.cn
  2. Update local history database
  3. Review today's AI prediction (hit / miss)
  4. AI analyzes trends → generates filter conditions → auto-filter → GL file
  5. Push results to Telegram
```

---

# FC3D_AI - 福彩3D AI智能分析工具

基于 Claude AI 大模型的福彩3D智能分析、自动过滤、定时推送系统。

## 功能特点

- **AI智能分析** — 使用 Claude Opus 4.6（Poe API，`output_effort: high` 高级思考模式）深度分析走势
- **16种过滤方法** — 和值、跨度、AC值、奇偶比、大小比、012路、组选类型、百/十/个位定位、重复号、和尾、质合比、连号、首尾差、必含号码、排除号码
- **一键出号** — AI分析→结构化JSON输出→自动过滤→生成GL文件（直选模式）
- **每日定时任务** — 22:00自动执行：获取开奖→复盘→生成次日方案→推送TG
- **Telegram Bot** — 全功能机器人，AI处理时显示"正在输入..."状态
- **命令行界面** — 交互式菜单，本地使用
- **GL文件兼容** — 输出兼容福彩3D霸主软件（GB18030编码）

## 快速开始

### 1. 安装依赖

```bash
pip install openai httpx python-telegram-bot[job-queue] apscheduler
```

### 2. 配置密钥

复制 `.env.example` 为 `.env`，填入你的密钥：

```bash
cp .env.example .env
```

`.env` 中需要填写：
- `POE_API_KEY` — Poe API 密钥（[获取地址](https://poe.com/api_key)）
- `TG_BOT_TOKEN` — Telegram Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）
- `TG_ADMIN_ID` — 你的 Telegram 用户ID（只有此ID可以操作机器人）

### 3. 运行

```bash
# 命令行模式（双击 启动.bat 也可以）
python main.py

# Telegram 机器人（双击 启动TG机器人.bat 也可以）
python tg_bot.py

# 后台定时任务
python scheduler.py --daemon
```

## TG Bot 命令

| 命令 | 功能 |
|------|------|
| `/filter` | ★ 一键AI过滤出号 |
| `/report` | AI详细分析报告 |
| `/review` | 复盘最新过滤结果 |
| `/stats` | 遗漏值/热冷号统计 |
| `/update` | 更新开奖数据 |
| `/ask 问题` | 自由提问AI |
| `/daily` | 手动触发每日任务 |

直接发送文字消息也会被当作AI提问处理。

## 工作流程

```
每天 22:00 自动执行（或手动触发 /daily）：
  1. 从中彩网获取当天开奖结果
  2. 更新本地历史数据
  3. 复盘今天的AI过滤方案（命中/未命中）
  4. AI分析走势 → 生成过滤条件 → 自动过滤 → 输出GL文件
  5. 推送结果到 Telegram
```

## 输出目录

```
FC3D_AI/
├── data/history_3d.csv     # 历史开奖数据
├── output/gl/              # GL过滤文件（兼容3D霸主）
│   ├── GL2026073-01.txt
│   └── ...
└── logs/                   # 运行日志
```

## 注意事项

- 默认模式为**直选**，非组六
- 如果过滤结果为0注，会自动放宽条件重新过滤
- 所有时间为北京时间 (UTC+8)
- **免责声明：本工具仅供学习研究，彩票投注有风险，请理性购彩**

## License

MIT
