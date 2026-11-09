import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
DATABASE_URL = os.getenv("SCM_DATABASE_URL", "sqlite:///runtime/scm.db")
TIMEZONE = ZoneInfo(os.getenv("SCM_TIMEZONE", "Asia/Shanghai"))


def utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
