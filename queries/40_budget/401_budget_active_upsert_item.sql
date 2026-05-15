insert into fin.budget_active (
  month_id,
  kind,
  category_code,
  amount
)
values (
  :month_id,
  :kind,
  :category_code,
  :amount
)
on conflict (month_id, kind, category_code)
do update
set
  amount = excluded.amount,
  updated_at = now()
returning
  month_id,
  kind,
  category_code,
  amount,
  updated_at;
