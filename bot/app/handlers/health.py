from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.pool import Database

router = Router()

HEALTH_SQL_PATH = "90_admin/900_health.sql"


@router.message(Command("health"))
async def cmd_health(
    message: Message,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    try:
        health_sql = sql_cache.get(HEALTH_SQL_PATH)
        if health_sql:
            await db.execute(health_sql)
        else:
            await db.fetchval("SELECT 1")

        await message.answer("DB OK")
    except Exception as exc:
        await message.answer(f"DB FAIL: {exc}")
