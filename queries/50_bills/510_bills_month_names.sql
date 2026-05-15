select
  b.bill_name
from fin.bills b
where b.month_id = :month_id
  and b.is_active = true
order by b.bill_name;
