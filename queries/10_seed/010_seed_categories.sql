insert into fin.expense_category (code)
values
  ('Food'),
  ('Entertainment'),
  ('Bills'),
  ('Personal'),
  ('Credits'),
  ('Health'),
  ('Shopping'),
  ('Other'),
  ('Savings'),
  ('Sport')
on conflict (code) do nothing;

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
