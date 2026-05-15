with bounds as (
  select
    :date_from_msk::timestamp as ts_from_msk,
    :date_to_msk::timestamp as ts_to_msk
)
select
  coalesce(sum(t.amount), 0) as clean_income
from fin.transactions t
cross join bounds b
where t.type = 'income'
  and t.income_category <> 'Other'
  and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
  and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow');
