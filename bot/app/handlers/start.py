from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.menu import MAIN_MENU

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "✅ <b>Finance Tracker is ready</b>\n\n"
        "Use the buttons below.\n"
        "Commands:\n"
        "• <code>/start</code> <code>/help</code> <code>/health</code>\n"
        "• <code>/expense</code> <code>/income</code>\n"
        "• <code>/stats</code> <code>/today</code> <code>/week</code> <code>/month</code> <code>/year</code>\n"
        "• <code>/last</code> <code>/budget</code> <code>/budget_expense</code> <code>/budget_income</code> <code>/bills</code>\n"
        "• <code>/set_bills</code> <code>/backup</code>",
        reply_markup=MAIN_MENU,
        parse_mode="HTML",
    )
