with bounds as (
  select
    :date_from_msk::timestamp as ts_from_msk,
    :date_to_msk::timestamp as ts_to_msk
),
agg as (
  select
    coalesce(sum(case when t.type = 'expense' then t.amount end), 0) as total_expense,
    coalesce(sum(case when t.type = 'income' then t.amount end), 0) as total_income
  from fin.transactions t
  cross join bounds b
  where t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
)
select
  a.total_expense,
  a.total_income,
  (a.total_income - a.total_expense) as balance
from agg a;
