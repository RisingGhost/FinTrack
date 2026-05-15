with bounds as (
  select
    to_date(:month_id || '-01', 'YYYY-MM-DD')::timestamp as ts_from_msk,
    (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month')::timestamp as ts_to_msk
),
planned as (
  select
    b.bill_name,
    b.planned_amount
  from fin.bills b
  where b.month_id = :month_id
    and b.is_active = true
),
paid as (
  select
    coalesce(t.comment, 'unexpected bill') as bill_name,
    sum(t.amount) as paid_amount
  from fin.transactions t
  cross join bounds b
  where t.type = 'expense'
    and t.expense_category = 'Bills'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by coalesce(t.comment, 'unexpected bill')
)
select
  p.bill_name,
  p.planned_amount,
  coalesce(pd.paid_amount, 0) as paid_amount,
  case
    when coalesce(pd.paid_amount, 0) = 0 then 'not_paid'
    when coalesce(pd.paid_amount, 0) < p.planned_amount then 'partial'
    else 'paid'
  end as status
from planned p
left join paid pd
  on pd.bill_name = p.bill_name
order by p.bill_name;
