import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher

from app.config import Settings, load_settings
from app.db.pool import Database
from app.db.sql_loader import load_sql_queries
from app.db.sql_params import bind_named_params
from app.handlers.access import setup_whitelist
from app.handlers.health import router as health_router
from app.handlers.mvp import router as mvp_router
from app.handlers.start import router as start_router

MSK = ZoneInfo("Europe/Moscow")
PATH_ARCHIVE_MONTH = "40_budget/403_budget_archive_month.sql"
PATH_CLEAR_BUDGET_MONTH = "40_budget/404_budget_active_clear_month.sql"
PATH_CLEAR_BILLS_MONTH = "50_bills/522_bills_clear_month.sql"


def _sql_from_cache(sql_cache: dict[str, str], path: str) -> str:
    sql = sql_cache.get(path)
    if sql is None:
        raise KeyError(f"SQL not found: {path}")
    return sql


async def _fetchrow_named(
    db: Database,
    sql_cache: dict[str, str],
    path: str,
    params: dict[str, object],
):
    sql = _sql_from_cache(sql_cache, path)
    converted_sql, args = bind_named_params(sql, params)
    return await db.fetchrow(converted_sql, *args)


def _seconds_until_next_minute() -> float:
    now = datetime.now(MSK)
    next_tick = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    return max((next_tick - now).total_seconds(), 0.5)


async def _archive_closed_months(dispatcher: Dispatcher) -> None:
    db: Database = dispatcher["db"]
    sql_cache: dict[str, str] = dispatcher["sql_cache"]

    months_rows = await db.fetch(
        """
        with active_months as (
          select month_id from fin.budget_active
          union
          select month_id
          from fin.bills
          where is_active = true
        )
        select am.month_id
        from active_months am
        where (
          (
            (to_date(am.month_id || '-01', 'YYYY-MM-DD') + interval '1 month' - interval '1 day')::date
            + time '23:59'
          ) <= (now() at time zone 'Europe/Moscow')
        )
        order by am.month_id
        """
    )

    for row in months_rows:
        month_id = str(row["month_id"])
        archive_result = await _fetchrow_named(
            db,
            sql_cache,
            PATH_ARCHIVE_MONTH,
            {"month_id": month_id},
        )
        clear_budget_result = await _fetchrow_named(
            db,
            sql_cache,
            PATH_CLEAR_BUDGET_MONTH,
            {"month_id": month_id},
        )
        clear_bills_result = await _fetchrow_named(
            db,
            sql_cache,
            PATH_CLEAR_BILLS_MONTH,
            {"month_id": month_id},
        )
        logging.info(
            "Monthly archive finalized for %s (archived=%s budget_deleted=%s bills_deleted=%s)",
            month_id,
            dict(archive_result) if archive_result else {},
            clear_budget_result["deleted_rows"] if clear_budget_result else 0,
            clear_bills_result["deleted_rows"] if clear_bills_result else 0,
        )


async def _monthly_archive_loop(dispatcher: Dispatcher) -> None:
    while True:
        try:
            await _archive_closed_months(dispatcher)
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.exception("Monthly archive tick failed")
        await asyncio.sleep(_seconds_until_next_minute())


async def on_startup(dispatcher: Dispatcher) -> None:
    settings: Settings = dispatcher["settings"]

    db = Database(settings.database_url)
    await db.connect()

    dispatcher["db"] = db
    dispatcher["sql_cache"] = load_sql_queries(settings.queries_dir)
    await _archive_closed_months(dispatcher)
    dispatcher["monthly_archive_task"] = asyncio.create_task(_monthly_archive_loop(dispatcher))
    logging.info("Bot startup completed")


async def on_shutdown(dispatcher: Dispatcher) -> None:
    archive_task: asyncio.Task | None = dispatcher.get("monthly_archive_task")
    if archive_task is not None:
        archive_task.cancel()
        try:
            await archive_task
        except asyncio.CancelledError:
            pass

    db: Database | None = dispatcher.get("db")
    if db is not None:
        await db.close()
    logging.info("Bot shutdown completed")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()

    bot = Bot(token=settings.tg_token)
    dp = Dispatcher()

    dp["settings"] = settings

    for r in (start_router, health_router, mvp_router):
        setup_whitelist(r, settings.tg_whitelist_tg_id)
        dp.include_router(r)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
