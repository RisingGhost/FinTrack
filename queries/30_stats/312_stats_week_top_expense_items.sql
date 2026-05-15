with bounds as (
  select
    date_trunc('week', now() at time zone 'Europe/Moscow') as ts_from_msk,
    date_trunc('week', now() at time zone 'Europe/Moscow') + interval '1 week' as ts_to_msk
)
select
  t.id,
  t.occurred_at at time zone 'Europe/Moscow' as ts_msk,
  t.expense_category as category,
  t.amount,
  t.comment
from fin.transactions t
cross join bounds b
where t.type = 'expense'
  and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
  and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
order by t.amount desc, t.occurred_at desc, t.id desc
limit 5;
