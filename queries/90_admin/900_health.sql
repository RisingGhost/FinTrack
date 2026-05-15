select
  now() as now_utc,
  (now() at time zone 'Europe/Moscow') as now_msk,
  current_database(),
  current_user;
