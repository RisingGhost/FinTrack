import os
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ---------------- Paths ----------------
BASE_DIR = Path(__file__).resolve().parent
QUERIES_DIR = BASE_DIR / "queries"

SQL = {
    # stats totals
    "today_totals":  QUERIES_DIR / "30_stats" / "300_stats_today_totals.sql",
    "week_totals":   QUERIES_DIR / "30_stats" / "310_stats_week_totals.sql",
    "month_totals":  QUERIES_DIR / "30_stats" / "320_stats_month_totals.sql",
    "year_totals":   QUERIES_DIR / "30_stats" / "330_stats_year_totals.sql",
    "range_totals":  QUERIES_DIR / "30_stats" / "340_stats_range_totals.sql",
    # top expense
    "today_top":     QUERIES_DIR / "30_stats" / "301_stats_today_top_expense.sql",
    "week_top":      QUERIES_DIR / "30_stats" / "311_stats_week_top_expense.sql",
    "month_top":     QUERIES_DIR / "30_stats" / "321_stats_month_top_expense.sql",
    "year_top":      QUERIES_DIR / "30_stats" / "331_stats_year_top_expense.sql",
    "range_top":     QUERIES_DIR / "30_stats" / "341_stats_range_top_expense.sql",
    # transactions
    "last_n":        QUERIES_DIR / "20_transactions" / "210_tx_last_n.sql",
    # budget
    "budget_remaining": QUERIES_DIR / "40_budget" / "410_budget_current_remaining_expense.sql",
    "budget_income_prog": QUERIES_DIR / "40_budget" / "411_budget_current_income_progress.sql",
    "budget_summary": QUERIES_DIR / "40_budget" / "412_budget_current_summary.sql",
    "budget_history_view": QUERIES_DIR / "40_budget" / "420_budget_history_month_view.sql",
    "budget_history_summary": QUERIES_DIR / "40_budget" / "421_budget_history_summary.sql",
}

# Extra queries (not from files): keep simple and explicit
SQL_MONTHS = """
select
  to_char(date_trunc('month', occurred_at at time zone 'Europe/Moscow'), 'YYYY-MM') as month_id
from fin.transactions
group by 1
order by 1;
"""

SQL_INCOME_BY_CAT_MONTH = """
with bounds as (
  select
    date_trunc('month', to_date(:month_id||'-01','YYYY-MM-DD')) as ts_from_msk,
    date_trunc('month', to_date(:month_id||'-01','YYYY-MM-DD')) + interval '1 month' as ts_to_msk
)
select
  t.income_category as category,
  sum(t.amount) as received
from fin.transactions t
cross join bounds b
where t.type = 'income'
  and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
  and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
group by 1
order by received desc, category asc;
"""

SQL_EXPENSE_BY_CAT_MONTH = """
with bounds as (
  select
    date_trunc('month', to_date(:month_id||'-01','YYYY-MM-DD')) as ts_from_msk,
    date_trunc('month', to_date(:month_id||'-01','YYYY-MM-DD')) + interval '1 month' as ts_to_msk
)
select
  t.expense_category as category,
  sum(t.amount) as spent
from fin.transactions t
cross join bounds b
where t.type = 'expense'
  and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
  and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
group by 1
order by spent desc, category asc;
"""

SQL_TOTALS_MONTH = """
with bounds as (
  select
    date_trunc('month', to_date(:month_id||'-01','YYYY-MM-DD')) as ts_from_msk,
    date_trunc('month', to_date(:month_id||'-01','YYYY-MM-DD')) + interval '1 month' as ts_to_msk
),
agg as (
  select
    coalesce(sum(case when t.type='expense' then t.amount end),0) as total_expense,
    coalesce(sum(case when t.type='income'  then t.amount end),0) as total_income
  from fin.transactions t
  cross join bounds b
  where t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
)
select total_expense, total_income, (total_income-total_expense) as balance
from agg;
"""

def read_sql(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")

def get_engine():
    load_dotenv(BASE_DIR / ".env")
    db = os.getenv("POSTGRES_DB", "fintracker")
    user = os.getenv("POSTGRES_USER", "finbot")
    pwd = os.getenv("POSTGRES_PASSWORD")
    if not pwd:
        raise RuntimeError("POSTGRES_PASSWORD not found in .env")
    url = f"postgresql+psycopg://{user}:{pwd}@localhost:5432/{db}"
    return create_engine(url, pool_pre_ping=True)

def df(engine, sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})

def df_from_file(engine, key: str, params: dict | None = None) -> pd.DataFrame:
    return df(engine, read_sql(SQL[key]), params=params)

def show_totals(title: str, d: pd.DataFrame):
    st.subheader(title)
    if d.empty:
        st.write("no rows")
        return
    row = d.iloc[0]
    st.metric("total_expense", float(row["total_expense"]))
    st.metric("total_income", float(row["total_income"]))
    st.metric("balance", float(row["balance"]))

# ---------------- UI ----------------
st.set_page_config(page_title="Finance Tracker", layout="wide")
st.title("Finance Tracker — Stats (MSK)")

engine = get_engine()

# Sidebar controls
st.sidebar.header("Period")
period = st.sidebar.selectbox(
    "Mode",
    ["today", "week", "month (current)", "year (current)", "month (pick)", "range"],
    index=2,
)

# Load available months from DB
months_df = df(engine, SQL_MONTHS)
available_months = months_df["month_id"].tolist() if not months_df.empty else []
default_month = available_months[-1] if available_months else datetime.now().strftime("%Y-%m")

picked_month = None
date_from = None
date_to = None

if period == "month (pick)":
    picked_month = st.sidebar.selectbox("month_id (YYYY-MM)", available_months or [default_month])
elif period == "range":
    # UI dates -> convert to timestamps bounds (MSK), right bound exclusive
    d1 = st.sidebar.date_input("date_from (MSK)", value=date.today().replace(day=1))
    d2 = st.sidebar.date_input("date_to (MSK, inclusive)", value=date.today())
    # make right bound exclusive by adding 1 day at 00:00
    date_from = datetime(d1.year, d1.month, d1.day, 0, 0, 0)
    date_to = datetime(d2.year, d2.month, d2.day, 0, 0, 0) + timedelta(days=1)

st.sidebar.divider()
st.sidebar.header("Extras")
last_n = st.sidebar.slider("last N transactions", min_value=5, max_value=100, value=20, step=5)
show_budget = st.sidebar.checkbox("show budget widgets", value=True)

# ---------------- Main area ----------------
# Totals + Top expense
c1, c2 = st.columns(2)

if period == "today":
    totals = df_from_file(engine, "today_totals")
    top = df_from_file(engine, "today_top")
    title = "Today (MSK)"
elif period == "week":
    totals = df_from_file(engine, "week_totals")
    top = df_from_file(engine, "week_top")
    title = "Week (MSK)"
elif period == "month (current)":
    totals = df_from_file(engine, "month_totals")
    top = df_from_file(engine, "month_top")
    title = "Current month (MSK)"
elif period == "year (current)":
    totals = df_from_file(engine, "year_totals")
    top = df_from_file(engine, "year_top")
    title = "Current year (MSK)"
elif period == "month (pick)":
    totals = df(engine, SQL_TOTALS_MONTH, {"month_id": picked_month})
    top = df_from_file(engine, "range_top", params={
        # reuse range_top by building bounds for month picked
        "date_from_msk": datetime.strptime(picked_month + "-01 00:00:00", "%Y-%m-%d %H:%M:%S"),
        "date_to_msk": (datetime.strptime(picked_month + "-01 00:00:00", "%Y-%m-%d %H:%M:%S") + timedelta(days=32)).replace(day=1),
    })
    title = f"Month {picked_month} (MSK)"
else:  # range
    totals = df_from_file(engine, "range_totals", {"date_from_msk": date_from, "date_to_msk": date_to})
    top = df_from_file(engine, "range_top", {"date_from_msk": date_from, "date_to_msk": date_to})
    title = f"Range {date_from.date()}..{(date_to - timedelta(days=1)).date()} (MSK)"

with c1:
    show_totals(title, totals)

with c2:
    st.subheader("Top expense categories (limit 5)")
    st.dataframe(top, use_container_width=True)

st.divider()

# Income / Expense breakdown for selected month
st.subheader("By categories (pick month)")

month_for_breakdown = st.selectbox("month_id (YYYY-MM)", available_months or [default_month], index=(len(available_months)-1 if available_months else 0))

b1, b2 = st.columns(2)
with b1:
    st.write("Income (actual) by category")
    inc = df(engine, SQL_INCOME_BY_CAT_MONTH, {"month_id": month_for_breakdown})
    st.dataframe(inc, use_container_width=True)

with b2:
    st.write("Expense (actual) by category")
    exp = df(engine, SQL_EXPENSE_BY_CAT_MONTH, {"month_id": month_for_breakdown})
    st.dataframe(exp, use_container_width=True)

st.divider()

# Last N transactions
st.subheader(f"Last {last_n} transactions")
last_df = df_from_file(engine, "last_n", {"limit_n": last_n})
st.dataframe(last_df, use_container_width=True)

# Budget widgets
if show_budget:
    st.divider()
    st.subheader("Budget (month pick)")

    month_for_budget = st.selectbox("budget month_id (YYYY-MM)", available_months or [default_month], index=(len(available_months)-1 if available_months else 0), key="budget_month")

    bsum = df_from_file(engine, "budget_summary", {"month_id": month_for_budget})
    if not bsum.empty:
        r = bsum.iloc[0]
        cA, cB, cC, cD, cE = st.columns(5)
        cA.metric("planned_end", float(r["planned_end"]))
        cB.metric("actual_end_now", float(r["actual_end_now"]))
        cC.metric("total_expense", float(r["total_expense"]))
        cD.metric("total_income", float(r["total_income"]))
        cE.metric("delta", float(r["actual_end_now"] - r["planned_end"]))

    bb1, bb2 = st.columns(2)
    with bb1:
        st.write("Remaining by expense category")
        rem = df_from_file(engine, "budget_remaining", {"month_id": month_for_budget})
        st.dataframe(rem, use_container_width=True)
    with bb2:
        st.write("Income progress by income category")
        prog = df_from_file(engine, "budget_income_prog", {"month_id": month_for_budget})
        st.dataframe(prog, use_container_width=True)

    st.write("History (archive plan vs actual)")
    hist_summary = df_from_file(engine, "budget_history_summary", {"month_id": month_for_budget})
    st.dataframe(hist_summary, use_container_width=True)

    hist_sql = read_sql(SQL["budget_history_view"])

    # split into SQL statements by ';' (simple, no extra deps)
    stmts = [s.strip() for s in hist_sql.split(";") if s.strip()]
    if len(stmts) >= 2:
        exp_view_sql = stmts[0]
        inc_view_sql = stmts[1]
        h1, h2 = st.columns(2)
        with h1:
            st.write("Expense (archive vs actual)")
            st.dataframe(df(engine, exp_view_sql, {"month_id": month_for_budget}), use_container_width=True)
        with h2:
            st.write("Income (archive vs actual)")
            st.dataframe(df(engine, inc_view_sql, {"month_id": month_for_budget}), use_container_width=True)
    else:
        st.warning("420_budget_history_month_view.sql should contain 2 SELECT statements separated by ';'")
        st.code(hist_sql, language="sql")