with bounds as (
  select
    ((:occurred_at_msk::timestamp - interval '10 minutes') at time zone 'Europe/Moscow') as from_utc,
    ((:occurred_at_msk::timestamp + interval '10 minutes') at time zone 'Europe/Moscow') as to_utc
)
select
  t.id,
  t.occurred_at,
  (t.occurred_at at time zone 'Europe/Moscow') as ts_msk,
  t.amount,
  t.type,
  t.expense_category,
  t.income_category,
  t.comment
from fin.transactions t
cross join bounds b
where t.type = :type::fin.transaction_type
  and t.amount = :amount
  and t.occurred_at >= b.from_utc
  and t.occurred_at <= b.to_utc
  and (
    (:type = 'expense' and t.expense_category = :category_code)
    or
    (:type = 'income' and t.income_category = :category_code)
  )
order by t.occurred_at desc, t.id desc
limit 5;
