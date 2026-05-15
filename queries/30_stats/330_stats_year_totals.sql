with bounds as (
  select
    date_trunc('year', now() at time zone 'Europe/Moscow') as ts_from_msk,
    date_trunc('year', now() at time zone 'Europe/Moscow') + interval '1 year' as ts_to_msk
),
tx as (
  select
    t.id,
    t.type,
    t.amount,
    t.occurred_at,
    t.income_category,
    t.comment,
    to_char(
      date_trunc('month', t.occurred_at at time zone 'Europe/Moscow'),
      'YYYY-MM'
    ) as month_id
  from fin.transactions t
  cross join bounds b
  where t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
),
month_totals as (
  select
    x.month_id,
    coalesce(sum(case when x.type = 'expense' then x.amount end), 0) as total_expense,
    coalesce(sum(case when x.type = 'income' then x.amount end), 0) as total_income,
    (
      coalesce(sum(case when x.type = 'income' then x.amount end), 0)
      - coalesce(sum(case when x.type = 'expense' then x.amount end), 0)
    ) as month_balance
  from tx x
  group by x.month_id
),
month_totals_with_prev as (
  select
    mt.month_id,
    mt.month_balance,
    lag(mt.month_balance) over (order by mt.month_id) as prev_month_balance
  from month_totals mt
),
carry_candidates as (
  select
    x.id,
    x.month_id,
    x.amount,
    x.occurred_at,
    case
      when lower(btrim(coalesce(x.comment, ''))) = 'last month' then 0
      else 1
    end as priority
  from tx x
  join month_totals_with_prev mp
    on mp.month_id = x.month_id
  where x.type = 'income'
    and x.income_category = 'Other'
    and mp.prev_month_balance is not null
    and (
      lower(btrim(coalesce(x.comment, ''))) = 'last month'
      or (
        nullif(btrim(coalesce(x.comment, '')), '') is null
        and x.amount = mp.prev_month_balance
      )
    )
),
carry_rows as (
  select distinct on (cc.month_id)
    cc.month_id,
    cc.amount
  from carry_candidates cc
  order by
    cc.month_id,
    cc.priority,
    cc.occurred_at,
    cc.id
),
agg as (
  select
    coalesce(sum(case when x.type = 'expense' then x.amount end), 0) as total_expense,
    (
      coalesce(sum(case when x.type = 'income' then x.amount end), 0)
      - coalesce((select sum(cr.amount) from carry_rows cr), 0)
    ) as total_income
  from tx x
)
select
  a.total_expense,
  a.total_income,
  (a.total_income - a.total_expense) as balance
from agg a;
