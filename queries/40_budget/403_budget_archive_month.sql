with archive_meta as (
  select
    (
      (
        (to_date(:month_id || '-01', 'YYYY-MM-DD') + interval '1 month' - interval '1 day')::date
        + time '23:59'
      ) at time zone 'Europe/Moscow'
    ) as archived_at
),
budget_source_rows as (
  select
    ba.month_id,
    ba.kind,
    ba.category_code,
    ba.amount,
    am.archived_at
  from fin.budget_active ba
  cross join archive_meta am
  where ba.month_id = :month_id
),
budget_upserted as (
  insert into fin.budget_archive (
    month_id,
    kind,
    category_code,
    amount,
    archived_at
  )
  select
    sr.month_id,
    sr.kind,
    sr.category_code,
    sr.amount,
    sr.archived_at
  from budget_source_rows sr
  on conflict (month_id, kind, category_code)
  do update
  set
    amount = excluded.amount,
    archived_at = excluded.archived_at
  returning 1
),
bills_source_rows as (
  select
    b.month_id,
    b.bill_name,
    b.planned_amount,
    am.archived_at
  from fin.bills b
  cross join archive_meta am
  where b.month_id = :month_id
    and b.is_active = true
),
bills_upserted as (
  insert into fin.bills_archive (
    month_id,
    bill_name,
    planned_amount,
    archived_at
  )
  select
    sr.month_id,
    sr.bill_name,
    sr.planned_amount,
    sr.archived_at
  from bills_source_rows sr
  on conflict (month_id, bill_name)
  do update
  set
    planned_amount = excluded.planned_amount,
    archived_at = excluded.archived_at
  returning 1
),
bills_deleted as (
  delete from fin.bills_archive ba
  where ba.month_id = :month_id
    and not exists (
      select 1
      from bills_source_rows bs
      where bs.month_id = ba.month_id
        and bs.bill_name = ba.bill_name
    )
  returning 1
)
select
  (
    (select count(*)::int from budget_source_rows)
    + (select count(*)::int from bills_source_rows)
  ) as archived_rows,
  (select count(*)::int from budget_source_rows) as budget_archived_rows,
  (select count(*)::int from bills_source_rows) as bills_archived_rows,
  (select count(*)::int from bills_deleted) as bills_deleted_rows
from (
  select count(*) as affected_rows
  from budget_upserted
) bu
cross join (
  select count(*) as affected_rows
  from bills_upserted
) u;
