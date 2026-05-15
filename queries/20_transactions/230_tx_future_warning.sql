select
  (
    :occurred_at_msk::timestamp >
    (now() at time zone 'Europe/Moscow')::timestamp
  ) as is_future_msk;
