with bounds as (
  select
    to_date(:month_id || '-01', 'YYYY-MM-DD')::timestamp as ts_from_msk,
    (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month')::timestamp as ts_to_msk
),
bills_rollup as (
  select
    count(*)::int as bills_count,
    coalesce(sum(b.planned_amount), 0) as bills_sum
  from fin.bills_archive b
  where b.month_id = :month_id
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
planned as (
  select
    (
      coalesce(
        sum(
          case
            when ba.kind = 'expense_limit' and ba.category_code <> 'Bills' then ba.amount
          end
        ),
        0
      )
      +
      (select bills_amount from bills_limit)
    ) as planned_expense,
    coalesce(sum(case when ba.kind = 'income_plan' then ba.amount end), 0) as planned_income
  from fin.budget_archive ba
  where ba.month_id = :month_id
),
actual as (
  select
    coalesce(sum(case when t.type = 'expense' then t.amount end), 0) as total_expense,
    coalesce(sum(case when t.type = 'income' then t.amount end), 0) as total_income
  from fin.transactions t
  cross join bounds b
  where t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
)
select
  :month_id as month_id,
  (p.planned_income - p.planned_expense) as planned_end,
  (a.total_income - a.total_expense) as actual_end,
  a.total_expense,
  a.total_income
from planned p
cross join actual a;
