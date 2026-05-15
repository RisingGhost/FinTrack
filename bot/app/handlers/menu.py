from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_EXPENSE = "💸 Expense"
BTN_INCOME = "💰 Income"
BTN_STATS = "🗓️ Planning"
BTN_BUDGET = "🧾 Budget"
BTN_LAST = "🕘 Recent operations"

BTN_CANCEL = "✖ Cancel"
BTN_BACK = "⬅ Back"
BTN_SKIP = "⏭ Skip"
BTN_CONFIRM = "✅ Confirm"
BTN_KEEP_AMOUNT = "↩ Keep amount"
BTN_SET_NEW_AMOUNT = "✏️ Set new"

BTN_DATE_NOW = "🕒 Now"
BTN_DATE_CUSTOM = "🗓 Enter date"
BTN_BUDGET_REBALANCE_FULL = "🔄 All"
BTN_BUDGET_REBALANCE_INCOME = "💰 Income"
BTN_BUDGET_REBALANCE_EXPENSE = "💸 Expenses"
BTN_BUDGET_VIEW_ALL = "📌 Overview"
BTN_BUDGET_VIEW_EXPENSE = "📉 Budget"
BTN_BUDGET_VIEW_INCOME = "📈 Income"
BTN_BUDGET_VIEW_BILLS = "📄 Bills"
BTN_BILLS_SETUP = "📝 Bills"
BTN_LAST_MONTH_ALL = "📅 All this month"
BTN_LAST_25 = "25 operations"
BTN_LAST_15 = "15 operations"

BTN_STATS_TODAY = "today"
BTN_STATS_WEEK = "week"
BTN_STATS_MONTH = "month"
BTN_STATS_YEAR = "year"
BTN_STATS_ARCHIVE = "🗂 Archive"


MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_INCOME), KeyboardButton(text=BTN_EXPENSE)],
        [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_BUDGET)],
        [KeyboardButton(text=BTN_LAST)],
    ],
    resize_keyboard=True,
)

STATS_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_BILLS_SETUP)],
        [KeyboardButton(text=BTN_BUDGET_REBALANCE_FULL)],
        [KeyboardButton(text=BTN_BUDGET_REBALANCE_INCOME)],
        [KeyboardButton(text=BTN_BUDGET_REBALANCE_EXPENSE)],
        [KeyboardButton(text=BTN_BACK)],
    ],
    resize_keyboard=True,
)

DATE_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_DATE_NOW), KeyboardButton(text=BTN_DATE_CUSTOM)],
        [KeyboardButton(text=BTN_CANCEL)],
    ],
    resize_keyboard=True,
)

COMMENT_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_SKIP)],
        [KeyboardButton(text=BTN_CANCEL)],
    ],
    resize_keyboard=True,
)

CONFIRM_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_CONFIRM), KeyboardButton(text=BTN_CANCEL)],
    ],
    resize_keyboard=True,
)

CANCEL_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
    resize_keyboard=True,
)

BUDGET_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_BUDGET_VIEW_ALL), KeyboardButton(text=BTN_BUDGET_VIEW_EXPENSE)],
        [KeyboardButton(text=BTN_BUDGET_VIEW_INCOME), KeyboardButton(text=BTN_BUDGET_VIEW_BILLS)],
        [KeyboardButton(text=BTN_STATS_ARCHIVE)],
        [KeyboardButton(text=BTN_BACK)],
    ],
    resize_keyboard=True,
)

BUDGET_ITEM_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_KEEP_AMOUNT), KeyboardButton(text=BTN_SET_NEW_AMOUNT)],
        [KeyboardButton(text=BTN_CANCEL)],
    ],
    resize_keyboard=True,
)

LAST_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_LAST_MONTH_ALL)],
        [KeyboardButton(text=BTN_LAST_25), KeyboardButton(text=BTN_LAST_15)],
        [KeyboardButton(text=BTN_BACK)],
    ],
    resize_keyboard=True,
)


def make_choices_menu(choices: list[str], include_cancel: bool = True) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []

    for item in choices:
        row.append(KeyboardButton(text=item))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    if include_cancel:
        rows.append([KeyboardButton(text=BTN_CANCEL)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
