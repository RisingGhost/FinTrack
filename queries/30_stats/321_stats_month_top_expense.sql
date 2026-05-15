with bounds as (
  select
    date_trunc('month', now() at time zone 'Europe/Moscow') as ts_from_msk,
    date_trunc('month', now() at time zone 'Europe/Moscow') + interval '1 month' as ts_to_msk
),
expense_totals as (
  select
    t.expense_category as category,
    sum(t.amount) as spent
  from fin.transactions t
  cross join bounds b
  where t.type = 'expense'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by t.expense_category
),
total as (
  select
    coalesce(sum(et.spent), 0) as total_expense
  from expense_totals et
)
select
  et.category,
  et.spent,
  et.spent / nullif(tt.total_expense, 0) as share
from expense_totals et
cross join total tt
order by et.spent desc, et.category asc
limit 5;
