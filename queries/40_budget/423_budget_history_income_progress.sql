with bounds as (
  select
    to_date(:month_id || '-01', 'YYYY-MM-DD')::timestamp as ts_from_msk,
    (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month')::timestamp as ts_to_msk
),
planned_by_category as (
  select
    ba.category_code,
    ba.amount as planned_amount
  from fin.budget_archive ba
  where ba.month_id = :month_id
    and ba.kind = 'income_plan'
),
received_by_category as (
  select
    t.income_category as category_code,
    sum(t.amount) as received_amount
  from fin.transactions t
  cross join bounds b
  where t.type = 'income'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by t.income_category
)
select
  ic.code as category_code,
  coalesce(pb.planned_amount, 0) as planned_amount,
  coalesce(rb.received_amount, 0) as received_amount,
  coalesce(rb.received_amount, 0) / nullif(coalesce(pb.planned_amount, 0), 0) as progress
from fin.income_category ic
left join planned_by_category pb
  on pb.category_code = ic.code
left join received_by_category rb
  on rb.category_code = ic.code
order by ic.code;
