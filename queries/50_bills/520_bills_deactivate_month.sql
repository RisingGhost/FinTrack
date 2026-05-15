update fin.bills
set
  is_active = false,
  updated_at = now()
where month_id = :month_id
  and is_active = true;
