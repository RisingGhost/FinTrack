with bounds as (
  select
    to_date(:month_id || '-01', 'YYYY-MM-DD')::timestamp as ts_from_msk,
    (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month')::timestamp as ts_to_msk
),
bills_rollup as (
  select
    count(*)::int as bills_count,
    coalesce(sum(b.planned_amount), 0) as bills_sum
  from fin.bills b
  where b.month_id = :month_id
    and b.is_active = true
),
legacy_bills as (
  select
    coalesce(sum(ba.amount), 0) as legacy_bills_sum
  from fin.budget_active ba
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
  from fin.budget_active ba
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
),
limits_by_category as (
  select
    ba.category_code,
    ba.amount as limit_amount
  from fin.budget_active ba
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
),
overspend as (
  select
    coalesce(
      sum(
        greatest(
          coalesce(sb.spent_amount, 0) - coalesce(lb.limit_amount, 0),
          0
        )
      ),
      0
    ) as overspend_amount
  from fin.expense_category ec
  left join limits_by_category lb
    on lb.category_code = ec.code
  left join spent_by_category sb
    on sb.category_code = ec.code
),
income_planned_by_category as (
  select
    ba.category_code,
    ba.amount as planned_amount
  from fin.budget_active ba
  where ba.month_id = :month_id
    and ba.kind = 'income_plan'
),
income_actual_by_category as (
  select
    t.income_category as category_code,
    sum(t.amount) as received_amount
  from fin.transactions t
  cross join bounds b
  where t.type = 'income'
    and t.occurred_at >= (b.ts_from_msk at time zone 'Europe/Moscow')
    and t.occurred_at <  (b.ts_to_msk   at time zone 'Europe/Moscow')
  group by t.income_category
),
income_over as (
  select
    coalesce(
      sum(
        greatest(
          coalesce(ia.received_amount, 0) - coalesce(ip.planned_amount, 0),
          0
        )
      ),
      0
    ) as over_income_amount
  from fin.income_category ic
  left join income_planned_by_category ip
    on ip.category_code = ic.code
  left join income_actual_by_category ia
    on ia.category_code = ic.code
)
select
  :month_id as month_id,
  (p.planned_income - p.planned_expense - o.overspend_amount + io.over_income_amount) as planned_end,
  (a.total_income - a.total_expense) as actual_end_now,
  a.total_expense,
  a.total_income
from planned p
cross join actual a
cross join overspend o
cross join income_over io;
