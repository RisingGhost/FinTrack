insert into fin.bills (
  month_id,
  bill_name,
  planned_amount,
  is_active
)
values (
  :month_id,
  :bill_name,
  :planned_amount,
  true
)
on conflict (month_id, bill_name)
do update
set
  planned_amount = excluded.planned_amount,
  is_active = true,
  updated_at = now()
returning
  id,
  month_id,
  bill_name,
  planned_amount,
  is_active,
  updated_at;
