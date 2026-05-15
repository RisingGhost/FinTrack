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
budget_expense as (
  select
    ba.category_code,
    ba.amount as budget_limit
  from fin.budget_archive ba
  where ba.month_id = :month_id
    and ba.kind = 'expense_limit'
    and ba.category_code <> 'Bills'
  union all
  select
    'Bills'::text as category_code,
    bl.bills_amount as budget_limit
  from bills_limit bl
),
actual_expense as (
  select
    t.expense_category as category_code,
    sum(t.amount) as actual_spent
  from fin.transactions t
  cross join bounds b
  where t.type = 'expense'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by t.expense_category
)
select
  ec.code as category_code,
  coalesce(be.budget_limit, 0) as budget_limit,
  coalesce(ae.actual_spent, 0) as actual_spent,
  coalesce(be.budget_limit, 0) - coalesce(ae.actual_spent, 0) as diff
from fin.expense_category ec
left join budget_expense be
  on be.category_code = ec.code
left join actual_expense ae
  on ae.category_code = ec.code
order by ec.code;
