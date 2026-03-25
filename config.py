# ============================================================
# FC3D_AI 配置文件
# ============================================================
# 敏感信息通过环境变量或 .env 文件加载，不要硬编码在此文件中。
# 复制 .env.example 为 .env 并填入你的密钥。
# ============================================================
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- 加载 .env 文件 ----------
_env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ==================== API 配置 ====================
API_PROVIDER = "poe"  # "poe" 或 "anthropic"

# Poe
POE_API_KEY = os.environ.get("POE_API_KEY", "")
POE_BASE_URL = "https://api.poe.com/v1"
POE_MODEL = "claude-opus-4.6"
POE_OUTPUT_EFFORT = "high"  # 思考等级: "low" / "medium" / "high" / "max" (max容易超时)

# Anthropic (备选)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# ==================== 路径配置 ====================
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOG_DIR = os.path.join(BASE_DIR, "logs")
HISTORY_CSV = os.path.join(DATA_DIR, "history_3d.csv")

# ==================== 分析配置 ====================
DEFAULT_RECENT_PERIODS = 50
MAX_CONTEXT_PERIODS = 100

# ==================== 定时任务配置 ====================
SCHEDULE_HOUR = 22       # 每天几点执行 (24小时制)
SCHEDULE_MINUTE = 0      # 几分执行

# ==================== Telegram Bot 配置 ====================
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_ADMIN_ID = int(os.environ.get("TG_ADMIN_ID", "0"))
