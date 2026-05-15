select
  to_char(date_trunc('month', t.occurred_at at time zone 'Europe/Moscow'), 'YYYY-MM') as month_id,
  t.type,
  count(*) as rows,
  sum(t.amount) as sum_amount
from fin.transactions t
group by
  to_char(date_trunc('month', t.occurred_at at time zone 'Europe/Moscow'), 'YYYY-MM'),
  t.type
order by month_id, t.type;
