from __future__ import annotations
import os
import logging
from dotenv import load_dotenv

load_dotenv()

TOKEN: str | None = os.getenv("TOKEN")
DB_PATH: str = os.getenv("DB_PATH", "bot.db")

LOG_LEVEL_NAME = (os.getenv("LOG_LEVEL") or "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

DEFAULT_NOTIFY_HOUR = int(os.getenv("DEFAULT_NOTIFY_HOUR", "9"))

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

if not TOKEN:
    raise RuntimeError("Нет TOKEN в .env — получите токен у @BotFather и положите его в .env")

__all__ = ["TOKEN", "DB_PATH", "DEFAULT_NOTIFY_HOUR", "LOG_LEVEL"]