with target_exists as (
  select exists (
    select 1
    from fin.budget_active ba
    where ba.month_id = :month_id
  ) as has_rows
),
source_active as (
  select max(ba.month_id) as month_id
  from fin.budget_active ba
  where ba.month_id < :month_id
),
source_archive as (
  select max(ba.month_id) as month_id
  from fin.budget_archive ba
  where ba.month_id < :month_id
),
source_month as (
  select
    case
      when sa.month_id is not null then sa.month_id
      else sar.month_id
    end as month_id,
    case
      when sa.month_id is not null then 'active'
      when sar.month_id is not null then 'archive'
      else null
    end as source_kind
  from source_active sa
  cross join source_archive sar
),
rows_to_copy as (
  select
    :month_id::char(7) as month_id,
    s.kind,
    s.category_code,
    s.amount
  from target_exists te
  cross join source_month sm
  join (
    select
      'active'::text as source_kind,
      ba.month_id,
      ba.kind,
      ba.category_code,
      ba.amount
    from fin.budget_active ba
    union all
    select
      'archive'::text as source_kind,
      ba.month_id,
      ba.kind,
      ba.category_code,
      ba.amount
    from fin.budget_archive ba
  ) s
    on s.source_kind = sm.source_kind
   and s.month_id = sm.month_id
  where te.has_rows = false
    and sm.source_kind is not null
),
inserted as (
  insert into fin.budget_active (
    month_id,
    kind,
    category_code,
    amount
  )
  select
    rtc.month_id,
    rtc.kind,
    rtc.category_code,
    rtc.amount
  from rows_to_copy rtc
  on conflict (month_id, kind, category_code) do nothing
  returning 1
)
select
  count(*)::int as inserted_rows
from inserted;
