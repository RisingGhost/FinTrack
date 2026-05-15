insert into fin.transactions (
  type,
  amount,
  occurred_at,
  expense_category,
  comment
)
values (
  'expense',
  :amount,
  (:occurred_at_msk::timestamp at time zone 'Europe/Moscow'),
  :expense_category,
  :comment
)
returning
  id,
  occurred_at,
  amount,
  expense_category,
  comment;
