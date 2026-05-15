insert into fin.transactions (
  type,
  amount,
  occurred_at,
  income_category,
  comment
)
values (
  'income',
  :amount,
  (:occurred_at_msk::timestamp at time zone 'Europe/Moscow'),
  :income_category,
  :comment
)
returning
  id,
  occurred_at,
  amount,
  income_category,
  comment;
