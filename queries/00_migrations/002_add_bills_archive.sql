create table if not exists fin.bills_archive (
  month_id char(7) not null,
  bill_name text not null,
  planned_amount numeric(14,2) not null check (planned_amount >= 0),
  archived_at timestamptz not null default now(),
  primary key (month_id, bill_name)
);

create index if not exists idx_fin_bills_archive_month_id
  on fin.bills_archive (month_id);
