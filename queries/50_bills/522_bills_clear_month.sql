with deleted as (
  delete from fin.bills
  where month_id = :month_id
  returning 1
)
select count(*)::int as deleted_rows
from deleted;
