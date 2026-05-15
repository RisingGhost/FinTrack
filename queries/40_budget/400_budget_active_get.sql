select
  ba.month_id,
  ba.kind,
  ba.category_code,
  ba.amount,
  ba.updated_at
from fin.budget_active ba
where ba.month_id = :month_id
order by ba.kind, ba.category_code;
