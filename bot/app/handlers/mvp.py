from __future__ import annotations

import json
import re
from html import escape
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message, ReplyKeyboardMarkup

from app.db.pool import Database
from app.db.sql_params import bind_named_params
from app.handlers.menu import (
    BTN_BACK,
    BTN_BILLS_SETUP,
    BTN_BUDGET,
    BTN_BUDGET_REBALANCE_EXPENSE,
    BTN_BUDGET_REBALANCE_FULL,
    BTN_BUDGET_REBALANCE_INCOME,
    BTN_BUDGET_VIEW_ALL,
    BTN_BUDGET_VIEW_BILLS,
    BTN_BUDGET_VIEW_EXPENSE,
    BTN_BUDGET_VIEW_INCOME,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_DATE_CUSTOM,
    BTN_DATE_NOW,
    BTN_EXPENSE,
    BTN_INCOME,
    BTN_KEEP_AMOUNT,
    BTN_LAST,
    BTN_LAST_15,
    BTN_LAST_25,
    BTN_LAST_MONTH_ALL,
    BTN_SET_NEW_AMOUNT,
    BTN_SKIP,
    BTN_STATS,
    BTN_STATS_ARCHIVE,
    BTN_STATS_MONTH,
    BTN_STATS_TODAY,
    BTN_STATS_WEEK,
    BTN_STATS_YEAR,
    BUDGET_ITEM_MENU,
    BUDGET_MENU,
    CANCEL_MENU,
    COMMENT_MENU,
    CONFIRM_MENU,
    DATE_MENU,
    LAST_MENU,
    MAIN_MENU,
    STATS_MENU,
    make_choices_menu,
)

router = Router()
MSK = ZoneInfo("Europe/Moscow")


class TxWizard(StatesGroup):
    waiting_amount = State()
    waiting_category = State()
    waiting_date_choice = State()
    waiting_custom_date = State()
    waiting_comment = State()
    waiting_bill = State()
    waiting_confirm = State()


class StatsArchiveWizard(StatesGroup):
    waiting_month = State()


class PlanningMenuWizard(StatesGroup):
    waiting_action = State()


class BudgetRebalanceWizard(StatesGroup):
    waiting_action = State()
    waiting_new_amount = State()


class BillsSetupWizard(StatesGroup):
    waiting_payload = State()


HELP_TEXT = (
    "ℹ️ <b>Use menu buttons</b>\n\n"
    "Expense: amount -> category -> comment -> confirm\n"
    "Income: amount -> category -> comment -> confirm\n"
    "Planning: bills / all / income / expenses\nArchive: open from Budget menu\n\n"
    "<b>Commands:</b>\n"
    "• <code>/start</code> <code>/help</code> <code>/health</code>\n"
    "• <code>/expense</code> <code>/income</code>\n"
    "• <code>/stats</code> <code>/today</code> <code>/week</code> <code>/month</code> <code>/year</code>\n"
    "• <code>/last [N]</code> <code>/budget</code> <code>/budget_expense</code>\n"
    "• <code>/budget_income</code> <code>/bills</code> <code>/set_bills</code>\n"
    "• <code>/backup</code> <code>/cancel</code>"
)

PATH_TX_INSERT_EXPENSE = "20_transactions/200_tx_insert_expense.sql"
PATH_TX_INSERT_INCOME = "20_transactions/201_tx_insert_income.sql"
PATH_TX_LAST_N = "20_transactions/210_tx_last_n.sql"
PATH_TX_MONTH_ALL = "20_transactions/211_tx_month_all.sql"
PATH_TX_DUP = "20_transactions/220_tx_possible_duplicate.sql"
PATH_TX_FUTURE = "20_transactions/230_tx_future_warning.sql"

PATH_STATS_TODAY_TOTALS = "30_stats/300_stats_today_totals.sql"
PATH_STATS_TODAY_TOP = "30_stats/301_stats_today_top_expense.sql"
PATH_STATS_TODAY_TOP_ITEMS = "30_stats/302_stats_today_top_expense_items.sql"
PATH_STATS_TODAY_CLEAN_INCOME = "30_stats/303_stats_today_income_clean.sql"
PATH_STATS_WEEK_TOTALS = "30_stats/310_stats_week_totals.sql"
PATH_STATS_WEEK_TOP = "30_stats/311_stats_week_top_expense.sql"
PATH_STATS_WEEK_TOP_ITEMS = "30_stats/312_stats_week_top_expense_items.sql"
PATH_STATS_WEEK_CLEAN_INCOME = "30_stats/313_stats_week_income_clean.sql"
PATH_STATS_MONTH_TOTALS = "30_stats/320_stats_month_totals.sql"
PATH_STATS_MONTH_TOP = "30_stats/321_stats_month_top_expense.sql"
PATH_STATS_MONTH_TOP_ITEMS = "30_stats/322_stats_month_top_expense_items.sql"
PATH_STATS_MONTH_CLEAN_INCOME = "30_stats/323_stats_month_income_clean.sql"
PATH_STATS_YEAR_TOTALS = "30_stats/330_stats_year_totals.sql"
PATH_STATS_YEAR_TOP = "30_stats/331_stats_year_top_expense.sql"
PATH_STATS_YEAR_TOP_ITEMS = "30_stats/332_stats_year_top_expense_items.sql"
PATH_STATS_YEAR_CLEAN_INCOME = "30_stats/333_stats_year_income_clean.sql"
PATH_STATS_RANGE_TOTALS = "30_stats/340_stats_range_totals.sql"
PATH_STATS_RANGE_TOP = "30_stats/341_stats_range_top_expense.sql"
PATH_STATS_RANGE_CLEAN_INCOME = "30_stats/342_stats_range_income_clean.sql"

PATH_BUDGET_AUTOCOPY = "40_budget/402_budget_autocopy_prev_month.sql"
PATH_BUDGET_ACTIVE_GET = "40_budget/400_budget_active_get.sql"
PATH_BUDGET_UPSERT = "40_budget/401_budget_active_upsert_item.sql"
PATH_BUDGET_REMAINING = "40_budget/410_budget_current_remaining_expense.sql"
PATH_BUDGET_PROGRESS = "40_budget/411_budget_current_income_progress.sql"
PATH_BUDGET_SUMMARY = "40_budget/412_budget_current_summary.sql"
PATH_BUDGET_HISTORY_SUMMARY = "40_budget/421_budget_history_summary.sql"
PATH_BUDGET_HISTORY_REMAINING = "40_budget/422_budget_history_remaining_expense.sql"
PATH_BUDGET_HISTORY_PROGRESS = "40_budget/423_budget_history_income_progress.sql"
PATH_BILLS_MONTH_STATUS = "50_bills/500_bills_month_status.sql"
PATH_BILLS_ARCHIVE_MONTH_STATUS = "50_bills/501_bills_archive_month_status.sql"
PATH_BILLS_MONTH_NAMES = "50_bills/510_bills_month_names.sql"
PATH_BILLS_DEACTIVATE_MONTH = "50_bills/520_bills_deactivate_month.sql"
PATH_BILLS_UPSERT_ITEM = "50_bills/521_bills_upsert_item.sql"
BILLS_UNEXPECTED = "unexpected bill"
INCOME_DISPLAY_ORDER = [
    "MLG з/п",
    "MLG аванс",
    "MLG нал",
    "MindSet",
    "Ivan_g",
    "Ivan_o",
    "Trofim",
    "Other",
]

PLANNING_STEP_BILLS = "bills"
PLANNING_STEP_INCOME = "income"
PLANNING_STEP_EXPENSE = "expense"
DEFAULT_BILLS_TEMPLATE = [
    "Rent",
    "Utilities",
    "Internet",
    "Mobile",
    "Subscriptions",
    "Transport",
    "Other",
]


def _month_id_now() -> str:
    return datetime.now(MSK).strftime("%Y-%m")


def _month_id_for_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _fmt_money(value: object) -> str:
    if value is None:
        return "0"
    try:
        whole = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{whole:,.0f}".replace(",", " ")
    except Exception:
        return str(value)


def _fmt_signed_money(value: object) -> str:
    try:
        amount = Decimal(str(value))
    except Exception:
        return str(value)
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{_fmt_money(abs(amount))}"


def _fmt_diff_money(value: object) -> str:
    try:
        amount = Decimal(str(value))
    except Exception:
        return str(value)
    if amount < 0:
        return f"-{_fmt_money(abs(amount))}"
    return _fmt_money(amount)


def _render_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def make_row(cells: tuple[str, ...]) -> str:
        parts: list[str] = []
        for i, cell in enumerate(cells):
            if i == 0:
                parts.append(cell.ljust(widths[i]))
            else:
                parts.append(cell.rjust(widths[i]))
        return "  ".join(parts)

    separator = "  ".join("-" * w for w in widths)
    lines = [make_row(headers), separator]
    lines.extend(make_row(row) for row in rows)
    return "\n".join(lines)


def _income_sort_key(code: str) -> tuple[int, str]:
    try:
        return (INCOME_DISPLAY_ORDER.index(code), code)
    except ValueError:
        return (len(INCOME_DISPLAY_ORDER), code)


def _parse_amount(raw: str) -> Decimal:
    normalized = raw.replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Amount must be a number") from exc

    if amount <= 0:
        raise ValueError("Amount must be > 0")

    return amount


def _parse_non_negative_amount(raw: str) -> Decimal:
    normalized = raw.replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Amount must be a number") from exc

    if amount < 0:
        raise ValueError("Amount must be >= 0")

    return amount


def _parse_custom_datetime(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed
        except ValueError:
            pass
    raise ValueError("Date format: YYYY-MM-DD HH:MM (or YYYY-MM-DD)")


def _month_bounds(month_id: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(f"{month_id}-01", "%Y-%m-%d")
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)
    return start, end


def _sql_from_cache(sql_cache: dict[str, str], path: str) -> str:
    sql = sql_cache.get(path)
    if sql is None:
        raise KeyError(f"SQL not found: {path}")
    return sql


def _budget_kind_label(kind: str) -> str:
    if kind == "expense_limit":
        return "Expense (limit)"
    return "Income (plan)"


def _budget_rebalance_mode_label(mode: str) -> str:
    if mode == "income":
        return "Income"
    if mode == "expense":
        return "Expenses"
    return "Full"


def _bill_status_emoji(status: str) -> str:
    if status == "paid":
        return "✅"
    if status == "partial":
        return "🟡"
    return "❌"


def _tx_confirm_summary(data: dict[str, object]) -> str:
    comment = data.get("comment")
    summary = [
        f"Type: {'Expense' if data.get('tx_type') == 'expense' else 'Income'}",
        f"Amount: {_fmt_money(data.get('amount'))}",
        f"Category: {data.get('category')}",
        f"Date: {data.get('occurred_at_msk')}",
        f"Comment: {comment or '-'}",
        "",
        "Confirm?",
    ]
    return "\n".join(summary)


async def _answer_lines_html(
    message: Message,
    lines: list[str],
    reply_markup: ReplyKeyboardMarkup,
    max_len: int = 3500,
) -> None:
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) > max_len:
            if current:
                chunks.append(current)
                current = line
            else:
                chunks.append(line[:max_len])
                current = line[max_len:]
        else:
            current = candidate

    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            reply_markup=reply_markup if i == 0 else None,
            parse_mode="HTML",
        )


def _fmt_amount_input(value: object) -> str:
    if value is None:
        return "0"
    try:
        whole = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return str(int(whole))
    except Exception:
        return str(value)


def _render_named_amount_lines(items: list[tuple[str, Decimal]]) -> str:
    return "\n".join(f"{name} {_fmt_amount_input(amount)}" for name, amount in items)


def _parse_named_amount_payload(raw: str) -> list[tuple[str, Decimal]]:
    text = raw.strip()
    if text.lower() in {"clear", "wipe", "-", "очистить"}:
        return []

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        raise ValueError("List is empty")

    result: list[tuple[str, Decimal]] = []
    seen: set[str] = set()
    separators = ("|", ";", " - ", ":")

    for line in lines:
        name_part = ""
        amount_part = ""

        for sep in separators:
            if sep in line:
                left, right = line.split(sep, 1)
                name_part = left.strip()
                amount_part = right.strip()
                break

        if not name_part:
            match = re.match(r"^(.+?)\s+([+-]?\d[\d\s]*(?:[.,]\d+)?)$", line)
            if match:
                name_part = match.group(1).strip()
                amount_part = match.group(2).strip()

        if not name_part or not amount_part:
            raise ValueError(f"Invalid line format: {line}")

        if len(name_part) > 120:
            raise ValueError(f"Name is too long: {name_part[:40]}...")

        key = name_part.casefold()
        if key in seen:
            raise ValueError(f"Duplicate name: {name_part}")
        seen.add(key)

        normalized_amount = (
            amount_part.replace(" ", "")
            .replace("\u00a0", "")
            .replace("\u202f", "")
        )
        amount = _parse_non_negative_amount(normalized_amount)
        result.append((name_part, amount))

    return result


def _parse_bills_payload(raw: str) -> list[tuple[str, Decimal]]:
    return _parse_named_amount_payload(raw)


async def _set_bills_for_month(
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
    bills: list[tuple[str, Decimal]],
) -> None:
    await _execute_named(
        db,
        sql_cache,
        PATH_BILLS_DEACTIVATE_MONTH,
        {"month_id": month_id},
    )
    for bill_name, planned_amount in bills:
        await _fetchrow_named(
            db,
            sql_cache,
            PATH_BILLS_UPSERT_ITEM,
            {
                "month_id": month_id,
                "bill_name": bill_name,
                "planned_amount": planned_amount,
            },
        )


async def _load_bills_setup_items(db: Database, month_id: str) -> list[tuple[str, Decimal]]:
    rows = await db.fetch(
        """
        select bill_name, planned_amount
        from fin.bills
        where month_id = $1
          and is_active = true
        order by bill_name
        """,
        month_id,
    )
    if rows:
        return [(str(r["bill_name"]), Decimal(str(r["planned_amount"] or 0))) for r in rows]
    return [(name, Decimal("0")) for name in DEFAULT_BILLS_TEMPLATE]


async def _budget_setup_meta(db: Database, step: str) -> tuple[str, list[str]]:
    if step == PLANNING_STEP_INCOME:
        rows = await db.fetch("select code from fin.income_category")
        categories = sorted([str(r["code"]) for r in rows], key=_income_sort_key)
        return "income_plan", categories

    if step == PLANNING_STEP_EXPENSE:
        rows = await db.fetch(
            "select code from fin.expense_category where code <> 'Bills' order by code"
        )
        categories = [str(r["code"]) for r in rows]
        return "expense_limit", categories

    raise ValueError(f"Unknown planning step: {step}")


async def _load_budget_setup_items(
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
    step: str,
) -> list[tuple[str, Decimal]]:
    await _fetchrow_named(db, sql_cache, PATH_BUDGET_AUTOCOPY, {"month_id": month_id})
    kind, categories = await _budget_setup_meta(db, step)
    active_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BUDGET_ACTIVE_GET,
        {"month_id": month_id},
    )
    active_map: dict[tuple[str, str], Decimal] = {
        (str(r["kind"]), str(r["category_code"])): Decimal(str(r["amount"] or 0))
        for r in active_rows
    }
    return [(code, active_map.get((kind, code), Decimal("0"))) for code in categories]


async def _apply_budget_setup_items(
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
    step: str,
    items: list[tuple[str, Decimal]],
) -> None:
    await _fetchrow_named(db, sql_cache, PATH_BUDGET_AUTOCOPY, {"month_id": month_id})
    kind, categories = await _budget_setup_meta(db, step)

    known_by_key = {code.casefold(): code for code in categories}
    parsed_map: dict[str, Decimal] = {}
    unknown_names: list[str] = []

    for name, amount in items:
        code = known_by_key.get(name.casefold())
        if code is None:
            unknown_names.append(name)
            continue
        parsed_map[code] = amount

    if unknown_names:
        unknown_text = ", ".join(sorted(unknown_names))
        raise ValueError(f"Unknown categories: {unknown_text}")

    for code in categories:
        await _fetchrow_named(
            db,
            sql_cache,
            PATH_BUDGET_UPSERT,
            {
                "month_id": month_id,
                "kind": kind,
                "category_code": code,
                "amount": parsed_map.get(code, Decimal("0")),
            },
        )


def _planning_step_title(step: str) -> str:
    if step == PLANNING_STEP_BILLS:
        return "Bills"
    if step == PLANNING_STEP_INCOME:
        return "Income"
    if step == PLANNING_STEP_EXPENSE:
        return "Expenses"
    return "Planning"


async def _start_planning_setup(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
    step: str,
    month_id: str,
    pending_steps: list[str] | None,
    return_to: str,
) -> None:
    pending_steps = pending_steps or []

    if step == PLANNING_STEP_BILLS:
        items = await _load_bills_setup_items(db, month_id)
    elif step in (PLANNING_STEP_INCOME, PLANNING_STEP_EXPENSE):
        items = await _load_budget_setup_items(db, sql_cache, month_id, step)
    else:
        raise ValueError(f"Unknown planning step: {step}")

    payload = _render_named_amount_lines(items)
    title = _planning_step_title(step)

    await state.set_state(BillsSetupWizard.waiting_payload)
    await state.update_data(
        planning_month_id=month_id,
        planning_step=step,
        planning_pending_steps=pending_steps,
        planning_return_to=return_to,
    )

    clear_hint = "Send <code>clear</code> to set an empty list."
    if step in (PLANNING_STEP_INCOME, PLANNING_STEP_EXPENSE):
        clear_hint = "If a category is missing in your message, it will be saved as 0."

    await message.answer(
        (
            f"🗓️ <b>Planning: {escape(title)} ({escape(month_id)})</b>\n"
            "Copy, edit and send back.\n"
            "Format: <code>Name Amount</code> (one line per item).\n\n"
            f"<pre>{escape(payload)}</pre>\n\n"
            f"{clear_hint}"
        ),
        reply_markup=CANCEL_MENU,
        parse_mode="HTML",
    )


async def _start_set_bills(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
    return_to: str,
) -> None:
    await _start_planning_setup(
        message,
        state,
        db,
        sql_cache,
        step=PLANNING_STEP_BILLS,
        month_id=month_id,
        pending_steps=[],
        return_to=return_to,
    )


async def _fetchrow_named(
    db: Database,
    sql_cache: dict[str, str],
    path: str,
    params: dict[str, object] | None = None,
):
    sql = _sql_from_cache(sql_cache, path)
    converted_sql, args = bind_named_params(sql, params or {})
    return await db.fetchrow(converted_sql, *args)


async def _fetch_named(
    db: Database,
    sql_cache: dict[str, str],
    path: str,
    params: dict[str, object] | None = None,
):
    sql = _sql_from_cache(sql_cache, path)
    converted_sql, args = bind_named_params(sql, params or {})
    return await db.fetch(converted_sql, *args)


async def _execute_named(
    db: Database,
    sql_cache: dict[str, str],
    path: str,
    params: dict[str, object] | None = None,
) -> str:
    sql = _sql_from_cache(sql_cache, path)
    converted_sql, args = bind_named_params(sql, params or {})
    return await db.execute(converted_sql, *args)


async def _log_parse_error(
    db: Database,
    input_text: str,
    error_text: str,
    context: dict[str, str],
) -> None:
    try:
        await db.execute(
            (
                "insert into fin.parse_error_log (input_text, error_text, context_json) "
                "values ($1, $2, $3::jsonb)"
            ),
            input_text,
            error_text,
            json.dumps(context, ensure_ascii=False),
        )
    except Exception:
        pass


async def _list_categories(db: Database, tx_type: str) -> list[str]:
    if tx_type == "expense":
        rows = await db.fetch("select code from fin.expense_category order by code")
        return [row["code"] for row in rows]

    rows = await db.fetch("select code from fin.income_category")
    codes = [str(row["code"]) for row in rows]
    return sorted(codes, key=_income_sort_key)


async def _build_budget_rebalance_items(
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
) -> list[dict[str, str]]:
    active_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BUDGET_ACTIVE_GET,
        {"month_id": month_id},
    )
    active_map: dict[tuple[str, str], Decimal] = {
        (str(r["kind"]), str(r["category_code"])): Decimal(str(r["amount"] or 0))
        for r in active_rows
    }

    expense_codes = [
        r["code"]
        for r in await db.fetch(
            "select code from fin.expense_category where code <> 'Bills' order by code"
        )
    ]
    income_codes = sorted(
        [str(r["code"]) for r in await db.fetch("select code from fin.income_category")],
        key=_income_sort_key,
    )

    items: list[dict[str, str]] = []
    for code in expense_codes:
        amount = active_map.get(("expense_limit", str(code)), Decimal("0"))
        items.append(
            {
                "kind": "expense_limit",
                "category_code": str(code),
                "amount": str(amount),
            }
        )

    for code in income_codes:
        amount = active_map.get(("income_plan", str(code)), Decimal("0"))
        items.append(
            {
                "kind": "income_plan",
                "category_code": str(code),
                "amount": str(amount),
            }
        )

    return items


def _select_budget_rebalance_items(
    items: list[dict[str, str]],
    mode: str,
) -> list[dict[str, str]]:
    if mode == "expense":
        return [item for item in items if item["kind"] == "expense_limit"]
    if mode == "income":
        return [item for item in items if item["kind"] == "income_plan"]
    return items


async def _upsert_budget_item(
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
    item: dict[str, str],
    amount: Decimal,
) -> None:
    await _fetchrow_named(
        db,
        sql_cache,
        PATH_BUDGET_UPSERT,
        {
            "month_id": month_id,
            "kind": item["kind"],
            "category_code": item["category_code"],
            "amount": amount,
        },
    )


async def _show_budget_rebalance_step(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    items: list[dict[str, str]] = data.get("budget_items", [])
    idx = int(data.get("budget_index", 0))
    month_id = str(data.get("budget_month_id", ""))
    mode = str(data.get("budget_mode", "full"))

    if idx >= len(items):
        return False

    item = items[idx]
    kind_label = _budget_kind_label(str(item["kind"]))
    current_amount = _fmt_money(item["amount"])
    total = len(items)

    await message.answer(
        (
            f"🗓️ <b>Planning {escape(month_id)}</b>\n"
            f"Mode: <b>{escape(_budget_rebalance_mode_label(mode))}</b>\n"
            f"Category <b>{idx + 1}/{total}</b>\n\n"
            f"Type: <b>{escape(kind_label)}</b>\n"
            f"Category: <b>{escape(str(item['category_code']))}</b>\n"
            f"Current amount: <b>{escape(current_amount)}</b> RUB\n\n"
            "Choose action:"
        ),
        reply_markup=BUDGET_ITEM_MENU,
        parse_mode="HTML",
    )
    return True


async def _finish_budget_rebalance(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    await state.clear()
    await message.answer("✅ Planning completed. Showing updated budget.")
    await _show_budget_general(message, db, sql_cache)


async def _after_budget_rebalance_items_done(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    data = await state.get_data()
    mode = str(data.get("budget_mode", ""))
    month_id = str(data.get("budget_month_id", _month_id_now()))
    if mode == "full":
        await message.answer("Next step: set bills list.")
        await _start_set_bills(
            message,
            state,
            db,
            sql_cache,
            month_id=month_id,
            return_to="after_full_rebalance",
        )
        return
    await _finish_budget_rebalance(message, state, db, sql_cache)


async def _tx_insert(
    db: Database,
    sql_cache: dict[str, str],
    tx_type: str,
    amount: Decimal,
    category: str,
    occurred_at_msk: datetime,
    comment: str | None,
) -> str:
    if tx_type == "expense" and category == "Bills" and (comment is None or str(comment).strip() == ""):
        comment = BILLS_UNEXPECTED

    if tx_type == "expense":
        category_exists = await db.fetchval(
            "select 1 from fin.expense_category where code = $1",
            category,
        )
        if category_exists is None:
            raise ValueError("Unknown expense category")
    else:
        category_exists = await db.fetchval(
            "select 1 from fin.income_category where code = $1",
            category,
        )
        if category_exists is None:
            raise ValueError("Unknown income category")

    duplicate_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_TX_DUP,
        {
            "type": tx_type,
            "amount": amount,
            "occurred_at_msk": occurred_at_msk,
            "category_code": category,
        },
    )
    future_row = await _fetchrow_named(
        db,
        sql_cache,
        PATH_TX_FUTURE,
        {"occurred_at_msk": occurred_at_msk},
    )

    if tx_type == "expense":
        inserted = await _fetchrow_named(
            db,
            sql_cache,
            PATH_TX_INSERT_EXPENSE,
            {
                "amount": amount,
                "occurred_at_msk": occurred_at_msk,
                "expense_category": category,
                "comment": comment,
            },
        )
    else:
        inserted = await _fetchrow_named(
            db,
            sql_cache,
            PATH_TX_INSERT_INCOME,
            {
                "amount": amount,
                "occurred_at_msk": occurred_at_msk,
                "income_category": category,
                "comment": comment,
            },
        )

    if inserted is None:
        raise RuntimeError("DB insert returned empty result")

    title = "✅ Expense added" if tx_type == "expense" else "✅ Income added"
    category_value = inserted["expense_category"] if tx_type == "expense" else inserted["income_category"]

    lines = [
        f"{title}: #{inserted['id']}",
        f"{_fmt_money(inserted['amount'])} RUB • {category_value}",
    ]

    if future_row and future_row["is_future_msk"]:
        lines.append("⚠️ Warning: date is in the future")
    if duplicate_rows:
        lines.append("⚠️ Warning: possible duplicate")

    return "\n".join(lines)


async def _stats_message(
    message: Message,
    db: Database,
    sql_cache: dict[str, str],
    title: str,
    totals_path: str,
    top_path: str,
    params: dict[str, object] | None = None,
    top_items_path: str | None = None,
    clean_income_path: str | None = None,
    reply_markup: ReplyKeyboardMarkup = STATS_MENU,
) -> None:
    totals_row = await _fetchrow_named(db, sql_cache, totals_path, params)
    top_rows = await _fetch_named(db, sql_cache, top_path, params)
    top_items_rows = await _fetch_named(db, sql_cache, top_items_path, params) if top_items_path else []
    clean_income_row = await _fetchrow_named(db, sql_cache, clean_income_path, params) if clean_income_path else None

    if totals_row is None:
        await message.answer(
            f"📊 <b>{escape(title)}</b>\nNo data",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return

    lines = [
        f"📊 <b>{escape(title)}</b>",
        f"Expense: <b>{escape(_fmt_money(totals_row['total_expense']))}</b> RUB",
        f"Income: <b>{escape(_fmt_money(totals_row['total_income']))}</b> RUB",
        f"Balance: <b>{escape(_fmt_money(totals_row['balance']))}</b> RUB",
    ]
    if clean_income_row is not None:
        lines.append(
            "Clean income: "
            f"<b>{escape(_fmt_money(clean_income_row['clean_income']))}</b> RUB"
        )

    if top_rows:
        lines.append("")
        lines.append("🏷 <b>Top expenses</b>:")
        for row in top_rows:
            share = Decimal(str(row["share"] or 0)) * Decimal("100")
            lines.append(
                f"• {escape(str(row['category']))}: "
                f"<b>{escape(_fmt_money(row['spent']))}</b> RUB "
                f"({share:.1f}%)"
            )

    if top_items_rows:
        lines.append("")
        lines.append("🧾 <b>5 largest expenses</b>:")
        for row in top_items_rows:
            ts = row["ts_msk"].strftime("%d.%m %H:%M") if row["ts_msk"] else "-"
            comment = str(row["comment"] or "").strip()
            comment_part = f" | {escape(comment[:28])}" if comment else ""
            lines.append(
                f"• {escape(str(ts))}: "
                f"<b>{escape(_fmt_money(row['amount']))}</b> RUB "
                f"({escape(str(row['category'] or '-'))}){comment_part}"
            )

    await _answer_lines_html(message, lines, reply_markup=reply_markup)


async def _show_last(
    message: Message,
    db: Database,
    sql_cache: dict[str, str],
    limit_n: int,
    reply_markup: ReplyKeyboardMarkup = LAST_MENU,
) -> None:
    rows = await _fetch_named(db, sql_cache, PATH_TX_LAST_N, {"limit_n": limit_n})

    if not rows:
        await message.answer("🕘 No operations yet", reply_markup=reply_markup)
        return

    lines = [f"🕘 <b>Last {limit_n} operations</b>"]
    for row in rows:
        category = row["expense_category"] or row["income_category"] or "-"
        comment = row["comment"] or ""
        ts = row["ts_msk"].strftime("%d.%m %H:%M") if row["ts_msk"] else "-"
        tx_type = "❌" if row["type"] == "expense" else "✅"
        comment_part = f" | {escape(comment[:28])}" if comment else ""
        lines.append(
            "• "
            f"#{row['id']} {ts} {tx_type}: "
            f"<b>{escape(_fmt_money(row['amount']))}</b> RUB "
            f"({escape(str(category))}){comment_part}"
        )

    await _answer_lines_html(message, lines, reply_markup=reply_markup)


async def _show_last_month(
    message: Message,
    db: Database,
    sql_cache: dict[str, str],
    month_id: str | None = None,
    reply_markup: ReplyKeyboardMarkup = LAST_MENU,
) -> None:
    month_id = month_id or _month_id_now()
    rows = await _fetch_named(
        db,
        sql_cache,
        PATH_TX_MONTH_ALL,
        {"month_id": month_id},
    )
    if not rows:
        await message.answer(f"🕘 No operations for {month_id}", reply_markup=reply_markup)
        return

    lines = [f"🕘 <b>All operations for {month_id}</b> ({len(rows)})"]
    for row in rows:
        category = row["expense_category"] or row["income_category"] or "-"
        comment = row["comment"] or ""
        ts = row["ts_msk"].strftime("%d.%m %H:%M") if row["ts_msk"] else "-"
        tx_type = "❌" if row["type"] == "expense" else "✅"
        comment_part = f" | {escape(comment[:28])}" if comment else ""
        lines.append(
            "• "
            f"#{row['id']} {ts} {tx_type}: "
            f"<b>{escape(_fmt_money(row['amount']))}</b> RUB "
            f"({escape(str(category))}){comment_part}"
        )

    await _answer_lines_html(message, lines, reply_markup=reply_markup)


async def _load_budget_payload(
    db: Database,
    sql_cache: dict[str, str],
) -> tuple[str, object | None, list[object], list[object]]:
    month_id = _month_id_now()
    await _fetchrow_named(db, sql_cache, PATH_BUDGET_AUTOCOPY, {"month_id": month_id})

    summary = await _fetchrow_named(
        db,
        sql_cache,
        PATH_BUDGET_SUMMARY,
        {"month_id": month_id},
    )
    remaining_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BUDGET_REMAINING,
        {"month_id": month_id},
    )
    progress_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BUDGET_PROGRESS,
        {"month_id": month_id},
    )
    return month_id, summary, remaining_rows, progress_rows


def _render_budget_summary_lines(summary: object) -> list[str]:
    actual_value = summary["actual_end_now"] if "actual_end_now" in summary else summary["actual_end"]
    return [
        "<b>I/O balance</b>",
        (
            "now/exp: "
            f"<b>{escape(_fmt_money(actual_value))}</b> / "
            f"<b>{escape(_fmt_money(summary['planned_end']))}</b> RUB"
        ),
    ]


def _render_expense_budget_table(remaining_rows: list[object]) -> str:
    expense_table_rows: list[tuple[str, str, str]] = []
    total_planned = Decimal("0")
    total_diff = Decimal("0")
    for row in sorted(remaining_rows, key=lambda r: Decimal(str(r["remaining_amount"] or 0))):
        planned_amount = Decimal(str(row["limit_amount"] or 0))
        diff_amount = Decimal(str(row["remaining_amount"] or 0))
        total_planned += planned_amount
        total_diff += diff_amount
        expense_table_rows.append(
            (
                str(row["category_code"]),
                _fmt_money(planned_amount),
                _fmt_diff_money(diff_amount),
            )
        )

    expense_table_rows.append(
        (
            "TOTAL",
            _fmt_money(total_planned),
            _fmt_diff_money(total_diff),
        )
    )
    return _render_table(("Category", "Planned", "Diff"), expense_table_rows)


def _render_income_budget_table(
    progress_rows: list[object],
    clean_income_value: object | None = None,
) -> str:
    income_table_rows: list[tuple[str, str, str]] = []
    total_received = Decimal("0")
    total_income_diff = Decimal("0")

    for row in sorted(progress_rows, key=lambda r: _income_sort_key(str(r["category_code"]))):
        planned_amount = Decimal(str(row["planned_amount"] or 0))
        received_amount = Decimal(str(row["received_amount"] or 0))
        diff_amount = received_amount - planned_amount

        total_received += received_amount
        total_income_diff += diff_amount

        income_table_rows.append(
            (
                str(row["category_code"]),
                _fmt_money(received_amount),
                _fmt_money(diff_amount),
            )
        )

    if clean_income_value is not None:
        income_table_rows.append(
            (
                "Clean income",
                _fmt_money(clean_income_value),
                "",
            )
        )

    income_table_rows.append(
        (
            "TOTAL",
            _fmt_money(total_received),
            _fmt_money(total_income_diff),
        )
    )
    return _render_table(("Category", "Actual", "Expected"), income_table_rows)


def _render_bills_status_table(bills_rows: list[object]) -> str:
    table_rows: list[tuple[str, str, str, str]] = []
    for row in bills_rows:
        table_rows.append(
            (
                str(row["bill_name"]),
                _fmt_money(row["planned_amount"]),
                _fmt_money(row["paid_amount"]),
                _bill_status_emoji(str(row["status"])),
            )
        )
    return _render_table(("Bill", "Plan", "Paid", "St"), table_rows)


async def _show_budget_general(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    month_id, summary, remaining_rows, progress_rows = await _load_budget_payload(db, sql_cache)
    if summary is None:
        await message.answer("Budget is empty", reply_markup=BUDGET_MENU)
        return
    start, end = _month_bounds(month_id)
    clean_income_row = await _fetchrow_named(
        db,
        sql_cache,
        PATH_STATS_RANGE_CLEAN_INCOME,
        {"date_from_msk": start, "date_to_msk": end},
    )
    clean_income_value = clean_income_row["clean_income"] if clean_income_row is not None else 0
    expense_table = _render_expense_budget_table(remaining_rows)
    income_table = _render_income_budget_table(progress_rows, clean_income_value=clean_income_value)
    await message.answer(
        f"<pre>{escape(expense_table)}</pre>"
        + "\n\n"
        + f"<pre>{escape(income_table)}</pre>"
        + "\n\n"
        + "\n".join(_render_budget_summary_lines(summary)),
        reply_markup=BUDGET_MENU,
        parse_mode="HTML",
    )


async def _show_budget_expense(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    _month_id, summary, remaining_rows, _progress_rows = await _load_budget_payload(db, sql_cache)
    if summary is None:
        await message.answer("Budget is empty", reply_markup=BUDGET_MENU)
        return
    expense_table = _render_expense_budget_table(remaining_rows)
    await message.answer(
        f"<pre>{escape(expense_table)}</pre>"
        + "\n\n"
        + "\n".join(_render_budget_summary_lines(summary)),
        reply_markup=BUDGET_MENU,
        parse_mode="HTML",
    )


async def _show_budget_income(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    month_id, summary, _remaining_rows, progress_rows = await _load_budget_payload(db, sql_cache)
    if summary is None:
        await message.answer("Budget is empty", reply_markup=BUDGET_MENU)
        return

    start, end = _month_bounds(month_id)
    clean_income_row = await _fetchrow_named(
        db,
        sql_cache,
        PATH_STATS_RANGE_CLEAN_INCOME,
        {"date_from_msk": start, "date_to_msk": end},
    )
    clean_income_value = clean_income_row["clean_income"] if clean_income_row is not None else 0

    income_table = _render_income_budget_table(progress_rows, clean_income_value=clean_income_value)
    await message.answer(
        f"<pre>{escape(income_table)}</pre>"
        + "\n\n"
        + "\n".join(_render_budget_summary_lines(summary)),
        reply_markup=BUDGET_MENU,
        parse_mode="HTML",
    )


async def _show_bills(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    month_id = _month_id_now()
    rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BILLS_MONTH_STATUS,
        {"month_id": month_id},
    )
    if not rows:
        await message.answer("Bills: list is empty", reply_markup=BUDGET_MENU)
        return

    table = _render_bills_status_table(rows)
    await message.answer(
        f"<pre>{escape(table)}</pre>",
        reply_markup=BUDGET_MENU,
        parse_mode="HTML",
    )


async def _show_archive_month_budget_tables(
    message: Message,
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
) -> None:
    start, end = _month_bounds(month_id)
    clean_income_row = await _fetchrow_named(
        db,
        sql_cache,
        PATH_STATS_RANGE_CLEAN_INCOME,
        {"date_from_msk": start, "date_to_msk": end},
    )
    clean_income_value = clean_income_row["clean_income"] if clean_income_row is not None else 0

    summary = await _fetchrow_named(
        db,
        sql_cache,
        PATH_BUDGET_HISTORY_SUMMARY,
        {"month_id": month_id},
    )
    expense_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BUDGET_HISTORY_REMAINING,
        {"month_id": month_id},
    )
    income_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BUDGET_HISTORY_PROGRESS,
        {"month_id": month_id},
    )
    bills_rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BILLS_ARCHIVE_MONTH_STATUS,
        {"month_id": month_id},
    )

    expense_table = _render_expense_budget_table(expense_rows)
    income_table = _render_income_budget_table(income_rows, clean_income_value=clean_income_value)
    bills_block = "no entries" if not bills_rows else f"<pre>{escape(_render_bills_status_table(bills_rows))}</pre>"

    header_lines = [f"🗂 <b>Archive budget {escape(month_id)}</b>"]
    if summary is not None:
        header_lines.extend(_render_budget_summary_lines(summary))

    await message.answer(
        "\n".join(header_lines)
        + "\n\n"
        + "<b>Budget</b>\n"
        + f"<pre>{escape(expense_table)}</pre>"
        + "\n\n"
        + "<b>Income</b>\n"
        + f"<pre>{escape(income_table)}</pre>"
        + "\n\n"
        + "<b>Bills</b>\n"
        + bills_block,
        reply_markup=BUDGET_MENU,
        parse_mode="HTML",
    )


async def _show_archive_month_stats(
    message: Message,
    db: Database,
    sql_cache: dict[str, str],
    month_id: str,
) -> None:
    start, end = _month_bounds(month_id)
    params = {"date_from_msk": start, "date_to_msk": end}

    totals_row = await _fetchrow_named(db, sql_cache, PATH_STATS_RANGE_TOTALS, params)
    top_rows = await _fetch_named(db, sql_cache, PATH_STATS_RANGE_TOP, params)
    clean_income_row = await _fetchrow_named(db, sql_cache, PATH_STATS_RANGE_CLEAN_INCOME, params)

    if totals_row is None:
        await message.answer(
            f"📊 <b>Stats: archive {escape(month_id)}</b>\nNo data",
            reply_markup=BUDGET_MENU,
            parse_mode="HTML",
        )
        return

    lines = [
        f"📊 <b>Stats: archive {escape(month_id)}</b>",
        f"Expense: <b>{escape(_fmt_money(totals_row['total_expense']))}</b> RUB",
        f"Income: <b>{escape(_fmt_money(totals_row['total_income']))}</b> RUB",
        f"Balance: <b>{escape(_fmt_money(totals_row['balance']))}</b> RUB",
        (
            "Clean income: "
            f"<b>{escape(_fmt_money(clean_income_row['clean_income'] if clean_income_row else 0))}</b> RUB"
        ),
    ]

    if top_rows:
        lines.append("")
        lines.append("🏷 <b>Top expenses</b>:")
        for row in top_rows:
            share = Decimal(str(row["share"] or 0)) * Decimal("100")
            lines.append(
                f"• {escape(str(row['category']))}: "
                f"<b>{escape(_fmt_money(row['spent']))}</b> RUB "
                f"({share:.1f}%)"
            )

    await _answer_lines_html(message, lines, reply_markup=BUDGET_MENU)
    await _show_archive_month_budget_tables(message, db, sql_cache, month_id)


async def _show_stats_archive_months(message: Message, db: Database, state: FSMContext) -> None:
    rows = await db.fetch(
        """
        with tx_months as (
            select to_char(date_trunc('month', occurred_at at time zone 'Europe/Moscow'), 'YYYY-MM') as month_id
            from fin.transactions
            group by 1
        ),
        ba_months as (
            select month_id from fin.budget_archive group by 1
        ),
        bills_months as (
            select month_id from fin.bills_archive group by 1
        )
        select month_id
        from (
            select month_id from tx_months
            union
            select month_id from ba_months
            union
            select month_id from bills_months
        ) x
        order by month_id desc
        """
    )
    months = [r["month_id"] for r in rows]

    if not months:
        await message.answer("Archive is empty", reply_markup=BUDGET_MENU)
        return

    await state.set_state(StatsArchiveWizard.waiting_month)
    await state.update_data(archive_months=months)

    choices = months[:24] + [BTN_BACK]
    await message.answer(
        "🗂 Choose archive month (YYYY-MM):",
        reply_markup=make_choices_menu(choices, include_cancel=True),
    )


async def _start_tx_wizard(
    message: Message,
    state: FSMContext,
    tx_type: str,
) -> None:
    await state.clear()
    await state.set_state(TxWizard.waiting_amount)
    await state.update_data(tx_type=tx_type)

    title = "expense" if tx_type == "expense" else "income"
    await message.answer(
        f"✍️ Add {title}.\nEnter amount:",
        reply_markup=CANCEL_MENU,
    )


async def _start_bills_pick_for_tx(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
    occurred_at_msk: datetime,
) -> None:
    month_id = _month_id_for_datetime(occurred_at_msk)
    rows = await _fetch_named(
        db,
        sql_cache,
        PATH_BILLS_MONTH_NAMES,
        {"month_id": month_id},
    )
    bill_choices = [str(r["bill_name"]) for r in rows]
    if BILLS_UNEXPECTED not in bill_choices:
        bill_choices.append(BILLS_UNEXPECTED)

    await state.update_data(bill_choices=bill_choices)
    await state.set_state(TxWizard.waiting_bill)
    await message.answer(
        "Choose bill for Bills:",
        reply_markup=make_choices_menu(bill_choices, include_cancel=True),
    )


async def _go_next_after_tx_date(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
    occurred_at_msk: datetime,
) -> None:
    data = await state.get_data()
    tx_type = data.get("tx_type")
    category = data.get("category")

    if tx_type == "expense" and category == "Bills":
        await _start_bills_pick_for_tx(message, state, db, sql_cache, occurred_at_msk)
        return

    await state.set_state(TxWizard.waiting_comment)
    await message.answer(
        "Comment (or Skip):",
        reply_markup=COMMENT_MENU,
    )


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
@router.message(F.text == "Cancel")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current is None:
        await message.answer("No active operation", reply_markup=MAIN_MENU)
    else:
        await message.answer("Operation cancelled", reply_markup=MAIN_MENU)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=MAIN_MENU, parse_mode="HTML")


@router.message(Command("stats"))
@router.message(F.text == BTN_STATS, StateFilter(None))
@router.message(F.text == "Planning", StateFilter(None))
async def cmd_stats(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(PlanningMenuWizard.waiting_action)
    await message.answer(
        "🗓️ Choose planning action:",
        reply_markup=STATS_MENU,
    )


@router.message(Command("today"))
@router.message(F.text == BTN_STATS_TODAY, StateFilter(None))
async def cmd_today(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _stats_message(
        message,
        db,
        sql_cache,
        "Stats: today",
        PATH_STATS_TODAY_TOTALS,
        PATH_STATS_TODAY_TOP,
        top_items_path=PATH_STATS_TODAY_TOP_ITEMS,
        clean_income_path=PATH_STATS_TODAY_CLEAN_INCOME,
    )


@router.message(Command("week"))
@router.message(F.text == BTN_STATS_WEEK, StateFilter(None))
async def cmd_week(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _stats_message(
        message,
        db,
        sql_cache,
        "Stats: week",
        PATH_STATS_WEEK_TOTALS,
        PATH_STATS_WEEK_TOP,
        top_items_path=PATH_STATS_WEEK_TOP_ITEMS,
        clean_income_path=PATH_STATS_WEEK_CLEAN_INCOME,
    )


@router.message(Command("month"))
@router.message(F.text == BTN_STATS_MONTH, StateFilter(None))
async def cmd_month(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _stats_message(
        message,
        db,
        sql_cache,
        "Stats: month",
        PATH_STATS_MONTH_TOTALS,
        PATH_STATS_MONTH_TOP,
        top_items_path=PATH_STATS_MONTH_TOP_ITEMS,
        clean_income_path=PATH_STATS_MONTH_CLEAN_INCOME,
    )


@router.message(Command("year"))
@router.message(F.text == BTN_STATS_YEAR, StateFilter(None))
async def cmd_year(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _stats_message(
        message,
        db,
        sql_cache,
        "Stats: year",
        PATH_STATS_YEAR_TOTALS,
        PATH_STATS_YEAR_TOP,
        top_items_path=PATH_STATS_YEAR_TOP_ITEMS,
        clean_income_path=PATH_STATS_YEAR_CLEAN_INCOME,
    )


@router.message(F.text == BTN_STATS_ARCHIVE, StateFilter(None))
async def menu_stats_archive(
    message: Message,
    db: Database,
    state: FSMContext,
) -> None:
    await _show_stats_archive_months(message, db, state)


@router.message(StatsArchiveWizard.waiting_month)
async def stats_archive_month_selected(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    text = (message.text or "").strip()

    if text == BTN_BACK:
        await state.clear()
        await message.answer("Budget menu", reply_markup=BUDGET_MENU)
        return

    data = await state.get_data()
    months: list[str] = data.get("archive_months", [])
    if text not in months:
        await message.answer("Choose a month using buttons")
        return

    await state.clear()

    await _show_archive_month_stats(message, db, sql_cache, text)


@router.message(F.text == BTN_BACK, StateFilter(PlanningMenuWizard.waiting_action))
@router.message(F.text == "Back", StateFilter(PlanningMenuWizard.waiting_action))
@router.message(F.text == BTN_BACK, StateFilter(None))
@router.message(F.text == "Back", StateFilter(None))
async def menu_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Main menu", reply_markup=MAIN_MENU)


@router.message(Command("last"))
async def cmd_last(
    message: Message,
    command: CommandObject,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    if not command.args:
        await _show_last(message, db, sql_cache, 5, reply_markup=LAST_MENU)
        return

    try:
        limit_n = int(command.args)
        if not (1 <= limit_n <= 50):
            raise ValueError
    except ValueError:
        await _log_parse_error(
            db,
            message.text or "",
            "Invalid /last argument",
            {"hint": "usage /last [1..50]"},
        )
        await message.answer("Format: /last [N], where N is 1..50")
        return

    await _show_last(message, db, sql_cache, limit_n, reply_markup=LAST_MENU)


@router.message(F.text == BTN_LAST, StateFilter(None))
@router.message(F.text == "Recent operations", StateFilter(None))
async def menu_last(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_last(message, db, sql_cache, 5, reply_markup=LAST_MENU)


@router.message(F.text == BTN_LAST_MONTH_ALL, StateFilter(None))
@router.message(F.text == "All this month", StateFilter(None))
async def menu_last_month_all(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_last_month(message, db, sql_cache, reply_markup=LAST_MENU)


@router.message(F.text == BTN_LAST_25, StateFilter(None))
@router.message(F.text == "25 operations", StateFilter(None))
async def menu_last_25(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_last(message, db, sql_cache, 25, reply_markup=LAST_MENU)


@router.message(F.text == BTN_LAST_15, StateFilter(None))
@router.message(F.text == "15 operations", StateFilter(None))
async def menu_last_15(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_last(message, db, sql_cache, 15, reply_markup=LAST_MENU)


@router.message(Command("budget"))
@router.message(Command("budget_all"))
@router.message(F.text == BTN_BUDGET, StateFilter(None))
@router.message(F.text == "Budget", StateFilter(None))
async def cmd_budget(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_budget_general(message, db, sql_cache)


@router.message(Command("budget_expense"))
@router.message(F.text == BTN_BUDGET_VIEW_EXPENSE, StateFilter(None))
async def cmd_budget_expense(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_budget_expense(message, db, sql_cache)


@router.message(Command("budget_income"))
@router.message(F.text == BTN_BUDGET_VIEW_INCOME, StateFilter(None))
async def cmd_budget_income(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_budget_income(message, db, sql_cache)


@router.message(Command("bills"))
@router.message(F.text == BTN_BUDGET_VIEW_BILLS, StateFilter(None))
async def cmd_bills(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_bills(message, db, sql_cache)


@router.message(Command("set_bills"))
@router.message(F.text == BTN_BILLS_SETUP, StateFilter(PlanningMenuWizard.waiting_action))
@router.message(F.text == "Set bills", StateFilter(PlanningMenuWizard.waiting_action))
async def cmd_set_bills(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    await _start_set_bills(
        message,
        state,
        db,
        sql_cache,
        month_id=_month_id_now(),
        return_to="manual",
    )


@router.message(BillsSetupWizard.waiting_payload)
async def planning_setup_payload(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    raw = (message.text or "").strip()
    data = await state.get_data()
    month_id = str(data.get("planning_month_id", _month_id_now()))
    step = str(data.get("planning_step", PLANNING_STEP_BILLS))
    pending_steps = [str(x) for x in data.get("planning_pending_steps", [])]
    return_to = str(data.get("planning_return_to", "manual"))

    try:
        parsed_items = _parse_named_amount_payload(raw)

        if step == PLANNING_STEP_BILLS:
            await _set_bills_for_month(db, sql_cache, month_id, parsed_items)
        elif step in (PLANNING_STEP_INCOME, PLANNING_STEP_EXPENSE):
            await _apply_budget_setup_items(db, sql_cache, month_id, step, parsed_items)
        else:
            raise ValueError(f"Unknown planning step: {step}")
    except ValueError as exc:
        await _log_parse_error(
            db,
            raw,
            str(exc),
            {
                "step": "planning_setup_payload",
                "planning_step": step,
                "month_id": month_id,
            },
        )
        await message.answer(str(exc))
        return

    current_title = _planning_step_title(step)

    if pending_steps:
        next_step = pending_steps[0]
        await message.answer(
            f"✅ {current_title} saved. Next: {_planning_step_title(next_step)}."
        )
        await _start_planning_setup(
            message,
            state,
            db,
            sql_cache,
            step=next_step,
            month_id=month_id,
            pending_steps=pending_steps[1:],
            return_to=return_to,
        )
        return

    if return_to == "after_full_rebalance":
        await message.answer("✅ Bills saved")
        await _finish_budget_rebalance(message, state, db, sql_cache)
        return

    await state.clear()
    await message.answer(f"✅ {current_title} saved. Showing updated budget.")
    await _show_budget_general(message, db, sql_cache)


@router.message(F.text == BTN_BUDGET_VIEW_ALL, StateFilter(None))
@router.message(F.text == "Overview", StateFilter(None))
async def menu_budget_all(message: Message, db: Database, sql_cache: dict[str, str]) -> None:
    await _show_budget_general(message, db, sql_cache)


async def _start_budget_rebalance_mode(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
    mode: str,
) -> None:
    month_id = _month_id_now()
    await _fetchrow_named(db, sql_cache, PATH_BUDGET_AUTOCOPY, {"month_id": month_id})
    items = _select_budget_rebalance_items(
        await _build_budget_rebalance_items(db, sql_cache, month_id),
        mode=mode,
    )

    if not items:
        await state.clear()
        await message.answer("No categories for planning", reply_markup=BUDGET_MENU)
        return

    await state.set_state(BudgetRebalanceWizard.waiting_action)
    await state.update_data(
        budget_month_id=month_id,
        budget_items=items,
        budget_index=0,
        budget_mode=mode,
    )
    await _show_budget_rebalance_step(message, state)


@router.message(F.text == BTN_BUDGET_REBALANCE_FULL, StateFilter(PlanningMenuWizard.waiting_action))
@router.message(F.text == "All", StateFilter(PlanningMenuWizard.waiting_action))
@router.message(F.text == "Planning", StateFilter(PlanningMenuWizard.waiting_action))
async def start_budget_rebalance_full(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    month_id = _month_id_now()
    await _start_planning_setup(
        message,
        state,
        db,
        sql_cache,
        step=PLANNING_STEP_EXPENSE,
        month_id=month_id,
        pending_steps=[PLANNING_STEP_INCOME, PLANNING_STEP_BILLS],
        return_to="manual",
    )


@router.message(F.text == BTN_BUDGET_REBALANCE_INCOME, StateFilter(PlanningMenuWizard.waiting_action))
@router.message(F.text == "Income", StateFilter(PlanningMenuWizard.waiting_action))
async def start_budget_rebalance_income(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    month_id = _month_id_now()
    await _start_planning_setup(
        message,
        state,
        db,
        sql_cache,
        step=PLANNING_STEP_INCOME,
        month_id=month_id,
        pending_steps=[],
        return_to="manual",
    )


@router.message(F.text == BTN_BUDGET_REBALANCE_EXPENSE, StateFilter(PlanningMenuWizard.waiting_action))
@router.message(F.text == "Expenses", StateFilter(PlanningMenuWizard.waiting_action))
async def start_budget_rebalance_expense(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    month_id = _month_id_now()
    await _start_planning_setup(
        message,
        state,
        db,
        sql_cache,
        step=PLANNING_STEP_EXPENSE,
        month_id=month_id,
        pending_steps=[],
        return_to="manual",
    )


@router.message(PlanningMenuWizard.waiting_action)
async def planning_menu_unknown_action(message: Message) -> None:
    await message.answer("Choose planning action using buttons", reply_markup=STATS_MENU)


@router.message(BudgetRebalanceWizard.waiting_action)
async def budget_rebalance_action(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    items: list[dict[str, str]] = data.get("budget_items", [])
    idx = int(data.get("budget_index", 0))
    month_id = str(data.get("budget_month_id", ""))

    if idx >= len(items):
        await _after_budget_rebalance_items_done(message, state, db, sql_cache)
        return

    current = items[idx]
    current_amount = Decimal(str(current.get("amount", "0")))

    if text in (BTN_KEEP_AMOUNT, "Keep amount"):
        await _upsert_budget_item(db, sql_cache, month_id, current, current_amount)
        idx += 1
        await state.update_data(budget_items=items, budget_index=idx)
        await state.set_state(BudgetRebalanceWizard.waiting_action)
        if not await _show_budget_rebalance_step(message, state):
            await _after_budget_rebalance_items_done(message, state, db, sql_cache)
        return

    if text in (BTN_SET_NEW_AMOUNT, "Set new"):
        await state.set_state(BudgetRebalanceWizard.waiting_new_amount)
        await message.answer(
            (
                f"✏️ Enter new amount (>= 0)\n"
                f"Type: <b>{escape(_budget_kind_label(str(current['kind'])))}</b>\n"
                f"Category: <b>{escape(str(current['category_code']))}</b>\n"
                f"Current: <b>{escape(_fmt_money(current_amount))}</b> RUB"
            ),
            parse_mode="HTML",
        )
        return

    await message.answer("Choose: keep amount or set new", reply_markup=BUDGET_ITEM_MENU)


@router.message(BudgetRebalanceWizard.waiting_new_amount)
async def budget_rebalance_new_amount(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    raw = (message.text or "").strip()
    data = await state.get_data()
    items: list[dict[str, str]] = data.get("budget_items", [])
    idx = int(data.get("budget_index", 0))
    month_id = str(data.get("budget_month_id", ""))

    if idx >= len(items):
        await _after_budget_rebalance_items_done(message, state, db, sql_cache)
        return

    current = items[idx]
    try:
        new_amount = _parse_non_negative_amount(raw)
    except ValueError as exc:
        await _log_parse_error(
            db,
            raw,
            str(exc),
            {
                "step": "budget_rebalance_new_amount",
                "kind": str(current.get("kind", "")),
                "category_code": str(current.get("category_code", "")),
            },
        )
        await message.answer(str(exc))
        return

    await _upsert_budget_item(db, sql_cache, month_id, current, new_amount)
    current["amount"] = str(new_amount)
    idx += 1
    await state.update_data(budget_items=items, budget_index=idx)
    await state.set_state(BudgetRebalanceWizard.waiting_action)

    if not await _show_budget_rebalance_step(message, state):
        await _after_budget_rebalance_items_done(message, state, db, sql_cache)


@router.message(Command("backup"))
async def cmd_backup(message: Message, db: Database) -> None:
    tx_rows = await db.fetch(
        (
            "select id, type, amount, occurred_at, expense_category, income_category, "
            "comment, created_at "
            "from fin.transactions "
            "order by occurred_at desc, id desc "
            "limit 50000"
        )
    )
    active_rows = await db.fetch(
        (
            "select month_id, kind, category_code, amount, updated_at "
            "from fin.budget_active order by month_id, kind, category_code"
        )
    )
    archive_rows = await db.fetch(
        (
            "select month_id, kind, category_code, amount, archived_at "
            "from fin.budget_archive order by month_id, kind, category_code"
        )
    )
    bills_rows = await db.fetch(
        (
            "select id, month_id, bill_name, planned_amount, is_active, created_at, updated_at "
            "from fin.bills order by month_id, bill_name"
        )
    )
    bills_archive_rows = await db.fetch(
        (
            "select month_id, bill_name, planned_amount, archived_at "
            "from fin.bills_archive order by month_id, bill_name"
        )
    )

    payload = {
        "generated_at": datetime.now(MSK).isoformat(),
        "transactions": [dict(row) for row in tx_rows],
        "budget_active": [dict(row) for row in active_rows],
        "budget_archive": [dict(row) for row in archive_rows],
        "bills_active": [dict(row) for row in bills_rows],
        "bills_archive": [dict(row) for row in bills_archive_rows],
        "note": "transactions are limited to 50000 newest rows",
    }

    content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
    filename = f"backup_{datetime.now(MSK).strftime('%Y%m%d_%H%M%S')}.json"

    await message.answer_document(
        BufferedInputFile(content, filename=filename),
        caption="Backup OK",
    )


@router.message(Command("expense"))
@router.message(F.text == BTN_EXPENSE, StateFilter(None))
@router.message(F.text == "Expense", StateFilter(None))
async def start_expense_wizard(
    message: Message,
    state: FSMContext,
) -> None:
    await _start_tx_wizard(message, state, "expense")


@router.message(Command("income"))
@router.message(F.text == BTN_INCOME, StateFilter(None))
@router.message(F.text == "Income", StateFilter(None))
async def start_income_wizard(
    message: Message,
    state: FSMContext,
) -> None:
    await _start_tx_wizard(message, state, "income")


@router.message(TxWizard.waiting_amount)
async def wizard_amount(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    raw = (message.text or "").strip()
    try:
        amount = _parse_amount(raw)
    except ValueError as exc:
        await _log_parse_error(db, message.text or "", str(exc), {"step": "amount"})
        await message.answer(str(exc))
        return

    data = await state.get_data()
    tx_type = data.get("tx_type", "expense")

    categories = await _list_categories(db, tx_type)
    if not categories:
        await state.clear()
        await message.answer("Categories are not configured", reply_markup=MAIN_MENU)
        return

    await state.update_data(amount=str(amount), categories=categories)
    await state.set_state(TxWizard.waiting_category)
    await message.answer(
        "Choose category:",
        reply_markup=make_choices_menu(categories, include_cancel=True),
    )


@router.message(TxWizard.waiting_category)
async def wizard_category(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    categories: list[str] = data.get("categories", [])

    if text not in categories:
        await message.answer("Choose a category using buttons")
        return

    await state.update_data(category=text)

    # Date/time picker is disabled for both flows for faster entry.
    dt = datetime.now(MSK).replace(tzinfo=None)
    await state.update_data(occurred_at_msk=dt.strftime("%Y-%m-%d %H:%M:%S"))
    await _go_next_after_tx_date(message, state, db, sql_cache, dt)


@router.message(TxWizard.waiting_date_choice)
async def wizard_date_choice(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    text = (message.text or "").strip()

    if text in (BTN_DATE_NOW, "Now"):
        dt = datetime.now(MSK).replace(tzinfo=None)
        await state.update_data(occurred_at_msk=dt.strftime("%Y-%m-%d %H:%M:%S"))
        await _go_next_after_tx_date(message, state, db, sql_cache, dt)
        return

    if text in (BTN_DATE_CUSTOM, "Enter date"):
        await state.set_state(TxWizard.waiting_custom_date)
        await message.answer("Enter date: YYYY-MM-DD HH:MM")
        return

    await message.answer(f"Choose: {BTN_DATE_NOW} or {BTN_DATE_CUSTOM}")


@router.message(TxWizard.waiting_custom_date)
async def wizard_custom_date(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    raw = (message.text or "").strip()
    try:
        dt = _parse_custom_datetime(raw)
    except ValueError as exc:
        await _log_parse_error(db, message.text or "", str(exc), {"step": "custom_date"})
        await message.answer(str(exc))
        return

    await state.update_data(occurred_at_msk=dt.strftime("%Y-%m-%d %H:%M:%S"))
    await _go_next_after_tx_date(message, state, db, sql_cache, dt)


@router.message(TxWizard.waiting_comment)
async def wizard_comment(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    comment = None if text in (BTN_SKIP, "Skip") else text

    await state.update_data(comment=comment)
    data = await state.get_data()

    await state.set_state(TxWizard.waiting_confirm)
    await message.answer(_tx_confirm_summary(data), reply_markup=CONFIRM_MENU)


@router.message(TxWizard.waiting_bill)
async def wizard_bill_choice(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    bill_choices: list[str] = data.get("bill_choices", [])

    if text not in bill_choices:
        await message.answer("Choose bill using buttons")
        return

    await state.update_data(comment=text)
    data = await state.get_data()
    await state.set_state(TxWizard.waiting_confirm)
    await message.answer(_tx_confirm_summary(data), reply_markup=CONFIRM_MENU)


@router.message(TxWizard.waiting_confirm)
async def wizard_confirm(
    message: Message,
    state: FSMContext,
    db: Database,
    sql_cache: dict[str, str],
) -> None:
    text = (message.text or "").strip()
    if text not in (BTN_CONFIRM, "Confirm"):
        await message.answer(f"Press {BTN_CONFIRM} or {BTN_CANCEL}")
        return

    data = await state.get_data()

    try:
        tx_type = data["tx_type"]
        amount = Decimal(str(data["amount"]))
        category = str(data["category"])
        occurred_at_msk = datetime.strptime(str(data["occurred_at_msk"]), "%Y-%m-%d %H:%M:%S")
        comment = data.get("comment")

        result_text = await _tx_insert(
            db,
            sql_cache,
            tx_type=tx_type,
            amount=amount,
            category=category,
            occurred_at_msk=occurred_at_msk,
            comment=comment,
        )
    except Exception as exc:
        await _log_parse_error(
            db,
            message.text or "",
            str(exc),
            {"step": "confirm"},
        )
        await state.clear()
        await message.answer(f"Save error: {exc}", reply_markup=MAIN_MENU)
        return

    await state.clear()
    await message.answer(result_text, reply_markup=MAIN_MENU)
