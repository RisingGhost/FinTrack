create schema if not exists fin;

do $$
begin
  if not exists (
    select 1
    from pg_type t
    join pg_namespace n on n.oid = t.typnamespace
    where t.typname = 'transaction_type'
      and n.nspname = 'fin'
  ) then
    create type fin.transaction_type as enum ('expense', 'income');
  end if;
end
$$;

create table if not exists fin.expense_category (
  code text primary key
);

create table if not exists fin.income_category (
  code text primary key
);

create table if not exists fin.transactions (
  id bigserial primary key,
  type fin.transaction_type not null,
  amount numeric(14,2) not null check (amount > 0),
  occurred_at timestamptz not null,
  expense_category text null references fin.expense_category(code),
  income_category text null references fin.income_category(code),
  comment text null,
  created_at timestamptz not null default now(),
  constraint category_matches_type check (
    (type = 'expense' and expense_category is not null and income_category is null)
    or
    (type = 'income' and income_category is not null and expense_category is null)
  )
);

create table if not exists fin.budget_active (
  month_id char(7) not null,
  kind text not null check (kind in ('expense_limit', 'income_plan')),
  category_code text not null,
  amount numeric(14,2) not null check (amount >= 0),
  updated_at timestamptz not null default now(),
  primary key (month_id, kind, category_code)
);

create table if not exists fin.budget_archive (
  month_id char(7) not null,
  kind text not null check (kind in ('expense_limit', 'income_plan')),
  category_code text not null,
  amount numeric(14,2) not null check (amount >= 0),
  archived_at timestamptz not null default now(),
  primary key (month_id, kind, category_code)
);

create table if not exists fin.parse_error_log (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  input_text text not null,
  error_text text not null,
  context_json jsonb null
);

create table if not exists fin.bills (
  id bigserial primary key,
  month_id char(7) not null,
  bill_name text not null,
  planned_amount numeric(14,2) not null check (planned_amount >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (month_id, bill_name)
);

create table if not exists fin.bills_archive (
  month_id char(7) not null,
  bill_name text not null,
  planned_amount numeric(14,2) not null check (planned_amount >= 0),
  archived_at timestamptz not null default now(),
  primary key (month_id, bill_name)
);

create index if not exists idx_fin_transactions_occurred_at
  on fin.transactions (occurred_at);

create index if not exists idx_fin_transactions_type
  on fin.transactions (type);

create index if not exists idx_fin_transactions_expense_category
  on fin.transactions (expense_category);

create index if not exists idx_fin_transactions_income_category
  on fin.transactions (income_category);

create index if not exists idx_fin_budget_active_month_id
  on fin.budget_active (month_id);

create index if not exists idx_fin_budget_archive_month_id
  on fin.budget_archive (month_id);

create index if not exists idx_fin_parse_error_log_created_at
  on fin.parse_error_log (created_at);

create index if not exists idx_fin_bills_month_id
  on fin.bills (month_id);

create index if not exists idx_fin_bills_archive_month_id
  on fin.bills_archive (month_id);
