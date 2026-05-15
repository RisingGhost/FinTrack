with bounds as (
  select
    to_date(:month_id || '-01', 'YYYY-MM-DD')::timestamp as ts_from_msk,
    (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month')::timestamp as ts_to_msk
),
bills_rollup as (
  select
    count(*)::int as bills_count,
    coalesce(sum(ba.planned_amount), 0) as bills_sum
  from fin.bills_archive ba
  where ba.month_id = :month_id
),
legacy_bills as (
  select
    coalesce(sum(ba.amount), 0) as legacy_bills_sum
  from fin.budget_archive ba
  where ba.month_id = :month_id
    and ba.kind = 'expense_limit'
    and ba.category_code = 'Bills'
),
bills_limit as (
  select
    case
      when br.bills_count > 0 then br.bills_sum
      else lb.legacy_bills_sum
    end as bills_amount
  from bills_rollup br
  cross join legacy_bills lb
),
limits_by_category as (
  select
    ba.category_code,
    ba.amount as limit_amount
  from fin.budget_archive ba
  where ba.month_id = :month_id
    and ba.kind = 'expense_limit'
    and ba.category_code <> 'Bills'
  union all
  select
    'Bills'::text as category_code,
    bl.bills_amount as limit_amount
  from bills_limit bl
),
spent_by_category as (
  select
    t.expense_category as category_code,
    sum(t.amount) as spent_amount
  from fin.transactions t
  cross join bounds b
  where t.type = 'expense'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by t.expense_category
)
select
  ec.code as category_code,
  coalesce(lb.limit_amount, 0) as limit_amount,
  coalesce(sb.spent_amount, 0) as spent_amount,
  coalesce(lb.limit_amount, 0) - coalesce(sb.spent_amount, 0) as remaining_amount
from fin.expense_category ec
left join limits_by_category lb
  on lb.category_code = ec.code
left join spent_by_category sb
  on sb.category_code = ec.code
order by ec.code;
