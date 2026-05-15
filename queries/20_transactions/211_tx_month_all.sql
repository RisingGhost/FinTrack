with bounds as (
  select
    to_date(:month_id || '-01', 'YYYY-MM-DD')::timestamp as ts_from_msk,
    (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month')::timestamp as ts_to_msk
)
select
  t.id,
  t.type,
  t.amount,
  t.occurred_at,
  (t.occurred_at at time zone 'Europe/Moscow') as ts_msk,
  t.expense_category,
  t.income_category,
  t.comment
from fin.transactions t
cross join bounds b
where t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
  and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
order by t.occurred_at desc, t.id desc;
