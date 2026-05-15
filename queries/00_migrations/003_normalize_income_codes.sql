begin;

insert into fin.income_category (code)
values
  ('MLG з/п'),
  ('MLG аванс'),
  ('MLG нал'),
  ('MindSet'),
  ('Ivan_g'),
  ('Ivan_o'),
  ('Trofim'),
  ('Other')
on conflict (code) do nothing;

update fin.transactions
set income_category = case income_category
  when 'МЛГ з/п' then 'MLG з/п'
  when 'МЛГ аванс' then 'MLG аванс'
  when 'МЛГ нал' then 'MLG нал'
  when 'Ваня Г.' then 'Ivan_g'
  when 'Ваня О.' then 'Ivan_o'
  when 'Иван' then 'Ivan_o'
  when 'Трофим' then 'Trofim'
  when 'ivan_g' then 'Ivan_g'
  when 'ivan_o' then 'Ivan_o'
  else income_category
end
where type = 'income'
  and income_category in (
    'МЛГ з/п',
    'МЛГ аванс',
    'МЛГ нал',
    'Ваня Г.',
    'Ваня О.',
    'Иван',
    'Трофим',
    'ivan_g',
    'ivan_o'
  );

with normalized as (
  select
    ba.month_id,
    ba.kind,
    case ba.category_code
      when 'МЛГ з/п' then 'MLG з/п'
      when 'МЛГ аванс' then 'MLG аванс'
      when 'МЛГ нал' then 'MLG нал'
      when 'Ваня Г.' then 'Ivan_g'
      when 'Ваня О.' then 'Ivan_o'
      when 'Иван' then 'Ivan_o'
      when 'Трофим' then 'Trofim'
      when 'ivan_g' then 'Ivan_g'
      when 'ivan_o' then 'Ivan_o'
      else ba.category_code
    end as category_code,
    sum(ba.amount) as amount,
    max(ba.updated_at) as updated_at
  from fin.budget_active ba
  where ba.kind = 'income_plan'
  group by
    ba.month_id,
    ba.kind,
    case ba.category_code
      when 'МЛГ з/п' then 'MLG з/п'
      when 'МЛГ аванс' then 'MLG аванс'
      when 'МЛГ нал' then 'MLG нал'
      when 'Ваня Г.' then 'Ivan_g'
      when 'Ваня О.' then 'Ivan_o'
      when 'Иван' then 'Ivan_o'
      when 'Трофим' then 'Trofim'
      when 'ivan_g' then 'Ivan_g'
      when 'ivan_o' then 'Ivan_o'
      else ba.category_code
    end
)
insert into fin.budget_active (
  month_id,
  kind,
  category_code,
  amount,
  updated_at
)
select
  n.month_id,
  n.kind,
  n.category_code,
  n.amount,
  n.updated_at
from normalized n
on conflict (month_id, kind, category_code)
do update
set
  amount = excluded.amount,
  updated_at = greatest(fin.budget_active.updated_at, excluded.updated_at);

delete from fin.budget_active ba
where ba.kind = 'income_plan'
  and ba.category_code in (
    'МЛГ з/п',
    'МЛГ аванс',
    'МЛГ нал',
    'Ваня Г.',
    'Ваня О.',
    'Иван',
    'Трофим',
    'ivan_g',
    'ivan_o'
  );

with normalized as (
  select
    ba.month_id,
    ba.kind,
    case ba.category_code
      when 'МЛГ з/п' then 'MLG з/п'
      when 'МЛГ аванс' then 'MLG аванс'
      when 'МЛГ нал' then 'MLG нал'
      when 'Ваня Г.' then 'Ivan_g'
      when 'Ваня О.' then 'Ivan_o'
      when 'Иван' then 'Ivan_o'
      when 'Трофим' then 'Trofim'
      when 'ivan_g' then 'Ivan_g'
      when 'ivan_o' then 'Ivan_o'
      else ba.category_code
    end as category_code,
    sum(ba.amount) as amount,
    max(ba.archived_at) as archived_at
  from fin.budget_archive ba
  where ba.kind = 'income_plan'
  group by
    ba.month_id,
    ba.kind,
    case ba.category_code
      when 'МЛГ з/п' then 'MLG з/п'
      when 'МЛГ аванс' then 'MLG аванс'
      when 'МЛГ нал' then 'MLG нал'
      when 'Ваня Г.' then 'Ivan_g'
      when 'Ваня О.' then 'Ivan_o'
      when 'Иван' then 'Ivan_o'
      when 'Трофим' then 'Trofim'
      when 'ivan_g' then 'Ivan_g'
      when 'ivan_o' then 'Ivan_o'
      else ba.category_code
    end
)
insert into fin.budget_archive (
  month_id,
  kind,
  category_code,
  amount,
  archived_at
)
select
  n.month_id,
  n.kind,
  n.category_code,
  n.amount,
  n.archived_at
from normalized n
on conflict (month_id, kind, category_code)
do update
set
  amount = excluded.amount,
  archived_at = greatest(fin.budget_archive.archived_at, excluded.archived_at);

delete from fin.budget_archive ba
where ba.kind = 'income_plan'
  and ba.category_code in (
    'МЛГ з/п',
    'МЛГ аванс',
    'МЛГ нал',
    'Ваня Г.',
    'Ваня О.',
    'Иван',
    'Трофим',
    'ivan_g',
    'ivan_o'
  );

delete from fin.income_category ic
where ic.code in (
  'МЛГ з/п',
  'МЛГ аванс',
  'МЛГ нал',
  'Ваня Г.',
  'Ваня О.',
  'Иван',
  'Трофим',
  'ivan_g',
  'ivan_o'
)
and not exists (
  select 1
  from fin.transactions t
  where t.type = 'income'
    and t.income_category = ic.code
);

commit;
