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
order by t.occurred_at desc, t.id desc
limit :limit_n;
