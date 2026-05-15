-- Expense categories: planned limit vs actual spent.
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
planned_expense as (
  select
    ba.category_code,
    ba.amount as planned_amount
  from fin.budget_archive ba
  where ba.month_id = :month_id
    and ba.kind = 'expense_limit'
    and ba.category_code <> 'Bills'
  union all
  select
    'Bills'::text as category_code,
    bl.bills_amount as planned_amount
  from bills_limit bl
),
actual_expense as (
  select
    t.expense_category as category_code,
    sum(t.amount) as actual_amount
  from fin.transactions t
  cross join bounds b
  where t.type = 'expense'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by t.expense_category
)
select
  ec.code as category_code,
  coalesce(pe.planned_amount, 0) as planned_amount,
  coalesce(ae.actual_amount, 0) as actual_amount,
  coalesce(ae.actual_amount, 0) / nullif(coalesce(pe.planned_amount, 0), 0) as ratio,
  coalesce(pe.planned_amount, 0) - coalesce(ae.actual_amount, 0) as diff
from fin.expense_category ec
left join planned_expense pe
  on pe.category_code = ec.code
left join actual_expense ae
  on ae.category_code = ec.code
order by ec.code;

-- Income categories: planned income vs actual received.
with bounds as (
  select
    to_date(:month_id || '-01', 'YYYY-MM-DD')::timestamp as ts_from_msk,
    (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month')::timestamp as ts_to_msk
),
planned_income as (
  select
    ba.category_code,
    ba.amount as planned_amount
  from fin.budget_archive ba
  where ba.month_id = :month_id
    and ba.kind = 'income_plan'
),
actual_income as (
  select
    t.income_category as category_code,
    sum(t.amount) as actual_amount
  from fin.transactions t
  cross join bounds b
  where t.type = 'income'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by t.income_category
)
select
  ic.code as category_code,
  coalesce(pi.planned_amount, 0) as planned_amount,
  coalesce(ai.actual_amount, 0) as actual_amount,
  coalesce(ai.actual_amount, 0) / nullif(coalesce(pi.planned_amount, 0), 0) as ratio,
  coalesce(ai.actual_amount, 0) - coalesce(pi.planned_amount, 0) as diff
from fin.income_category ic
left join planned_income pi
  on pi.category_code = ic.code
left join actual_income ai
  on ai.category_code = ic.code
order by ic.code;
