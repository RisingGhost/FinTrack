# Fin_Tracker — Project Map (локальный код)

## 1) Снимок
- Путь: `/Users/boriskov/Documents/folder/Fin_Tracker`
- Стек: `Python + aiogram 3 + asyncpg + PostgreSQL`
- Документ отражает текущее локальное состояние репозитория.

## 2) Что это за проект
Telegram-бот для учета личных финансов с фокусом на:
- быстрый ввод дохода/расхода через wizard,
- месячный бюджет (расходы + доходы),
- bills как отдельный учет регулярных платежей,
- статистику по периодам,
- архив закрытых месяцев,
- выгрузку backup в Telegram и shell-backup скриптом.

## 3) Корневая структура
- `docker-compose.yaml`: сервисы `db` (Postgres 16) и `bot`
- `docker/Dockerfile`: контейнер бота
- `bot/requirements.txt`: зависимости (`aiogram`, `asyncpg`)
- `bot/app/main.py`: запуск бота + lifecycle + monthly archive loop
- `bot/app/config.py`: env-конфиг
- `bot/app/db/*`: DB pool, SQL loader, named params binder
- `bot/app/handlers/start.py`: `/start`
- `bot/app/handlers/health.py`: `/health`
- `bot/app/handlers/access.py`: whitelist middleware
- `bot/app/handlers/menu.py`: все reply-кнопки
- `bot/app/handlers/mvp.py`: основной продуктовый сценарий
- `queries/*`: SQL по доменным папкам
- `scripts/create_backup.sh`: резервное копирование проекта + БД

## 4) Runtime-архитектура
### 4.1 Сервисы
- `db`: Postgres с healthcheck `pg_isready`
- `bot`: Python-процесс `python -m app.main`

### 4.2 Startup в `main.py`
1. Читает env (`load_settings`).
2. Поднимает `asyncpg` pool (`min=1`, `max=5`).
3. Загружает все `*.sql` в memory-cache (`dict[path -> text]`).
4. Выполняет `_archive_closed_months()` один раз на старте.
5. Стартует фоновой цикл `_monthly_archive_loop()` (проверка каждую минуту).
6. Запускает polling aiogram.

### 4.3 Shutdown
- останавливает фоновый monthly task,
- закрывает db pool.

## 5) Конфигурация (env)
Обязательные переменные:
- `TG_TOKEN`
- `TG_WHITELIST_TG_ID` (int)
- `DATABASE_URL`
- `QUERIES_DIR`

`.env.example` содержит шаблон для Postgres + Telegram.

## 6) DB модель (`fin` schema)
### Справочники
- `expense_category(code)`
- `income_category(code)`

### Транзакции
- `transactions`
  - `type`: `expense` / `income` (enum)
  - `amount > 0`
  - `occurred_at` (timestamptz)
  - `expense_category`/`income_category` (взаимоисключающие)
  - `comment`, `created_at`

### Бюджет
- `budget_active(month_id, kind, category_code, amount, updated_at)`
- `budget_archive(month_id, kind, category_code, amount, archived_at)`
- `kind`: `expense_limit` или `income_plan`

### Bills
- `bills(month_id, bill_name, planned_amount, is_active, ...)`
- `bills_archive(month_id, bill_name, planned_amount, archived_at)`

### Логи
- `parse_error_log` — лог ошибок парсинга пользовательского ввода.

## 7) SQL-слои
### `queries/20_transactions`
- insert expense/income
- последние N операций
- все операции за месяц
- проверка возможного дубля
- проверка даты в будущем

### `queries/30_stats`
- today/week/month/year/range:
  - totals (расход/доход/баланс),
  - top expense categories,
  - top expense items,
  - clean income (`income_category <> 'Other'`).
- `330_stats_year_totals.sql`: корректирует годовой доход, чтобы не удваивать переносы `last month`.

### `queries/40_budget`
- чтение/апсерт active-бюджета,
- автокопия бюджета на новый месяц (`402_budget_autocopy_prev_month.sql`),
- таблицы текущего месяца (remaining/progress/summary),
- таблицы архива (history_*),
- архивирование закрытого месяца (`403`),
- очистка active после архива (`404`).

### `queries/50_bills`
- статусы bills за месяц и архив,
- имена bills для picker в расходе,
- deactivate + upsert bills,
- очистка bills месяца.

### `queries/90_admin`
- `900_health.sql`
- QA-запросы сверок по данным.

## 8) Telegram-функционал (handlers)

## 8.1 Доступ
`WhitelistMiddleware` (в `access.py`) проверяет `from_user.id`.
Если не whitelist — `Access denied`.

## 8.2 Start/Health
- `/start`: приветствие + список команд + `MAIN_MENU`.
- `/health`: выполняет SQL health-check (или fallback `SELECT 1`) и пишет `DB OK/FAIL`.

## 8.3 Меню (`menu.py`)
Главное меню:
- `💰 Income`
- `💸 Expense`
- `🗓️ Planning`
- `🧾 Budget`
- `🕘 Recent operations`

Planning меню:
- `📝 Bills`
- `🔄 All`
- `💰 Income`
- `💸 Expenses`
- `⬅ Back`

Budget меню:
- `📌 Overview`
- `📉 Budget`
- `📈 Income`
- `📄 Bills`
- `🗂 Archive`
- `⬅ Back`

Last меню:
- `📅 All this month`
- `25 operations`
- `15 operations`
- `⬅ Back`

## 8.4 Wizard добавления транзакции (`mvp.py`)
Текущий пользовательский флоу (`expense` и `income`):
1. ввод суммы,
2. выбор категории,
3. автоматическая установка времени `now` (МСК),
4. комментарий,
5. подтверждение.

Особенность для `Bills` в расходах:
- после даты (автопоставленной) открывается picker bill-названий из `fin.bills` по `month_id`;
- если bill не найден/не выбран и комментарий пуст — ставится `unexpected bill`.

Проверки:
- корректность суммы,
- категория существует,
- возможный дубль,
- предупреждение про дату в будущем (в текущем флоу почти неактуально, так как дата auto-now).

Примечание:
- состояния `waiting_date_choice`/`waiting_custom_date` в коде есть, но в текущем UI-флоу не используются.

## 8.5 Последние операции
- `/last [N]` (1..50)
- кнопка `Recent operations` сразу показывает последние 5
- быстрые кнопки: `All this month`, `25 operations`, `15 operations`
- формат: `#id`, дата МСК, тип (❌/✅), сумма, категория, comment.

## 8.6 Бюджет
- `/budget` или кнопка `🧾 Budget` -> общий экран:
  - таблица расходов (`Planned`, `Diff`),
  - таблица доходов (`Actual`, `Expected`),
  - строка `Clean income`,
  - `I/O balance now/exp` в конце.
- отдельные команды: `/budget_expense`, `/budget_income`, `/bills`.
- перед чтением бюджета запускается SQL автокопии `402` для текущего месяца.

## 8.7 Planning (bulk-настройка)
Точка входа:
- кнопка `🗓️ Planning` или `/stats`.

Действия:
- `📝 Bills` -> открывает текущий список bills в формате `Name Amount` для copy/paste-редактирования,
- `💰 Income` -> открывает текущий income-план в формате `Name Amount`,
- `💸 Expenses` -> открывает текущий expense-план (без `Bills`) в формате `Name Amount`,
- `🔄 All` -> запускает последовательный сценарий: `Expenses -> Income -> Bills`.

Поведение:
- пользователь получает предзаполненный текстовый шаблон,
- редактирует суммы,
- отправляет обратно одним сообщением,
- бот валидирует и сохраняет,
- planning-действия доступны только в FSM-состоянии меню Planning (исключает конфликт с `💰 Income` на главном экране).

## 8.8 Bills / Income / Expenses setup
Общий формат ввода:
- одна строка = один элемент,
- формат: `Name Amount` (также поддержаны разделители `|`, `;`, ` - `, `:`),
- пример:
  - `Rent 0`
  - `Utilities 0`
  - `Internet 0`
- очистка: `clear`, `wipe`, `-`, `очистить`.

Правила сохранения:
- bills: запись через deactivate + upsert,
- income/expenses: unknown-категории отклоняются с ошибкой,
- для income/expenses отсутствующие в сообщении категории сохраняются как `0`.

## 8.9 Статистика и архив
- Быстрая статистика (`today/week/month/year`) доступна slash-командами:
  - `/today`, `/week`, `/month`, `/year`
  - в UI-кнопках верхнего уровня не показывается.
- Обычная статистика выводит:
  - totals,
  - топ категорий расходов,
  - топ-5 отдельных расходных операций,
  - clean income.
- Архив:
  - кнопка `🗂 Archive` из Budget-меню,
  - выбор месяца,
  - stats по месяцу,
  - таблицы Budget/Income/Bills архивного месяца.

## 8.10 Backup команда
`/backup`:
- собирает JSON (transactions + budget active/archive + bills active/archive),
- ограничение: до 50000 последних транзакций,
- отдает файл документом в Telegram.

## 9) Месячный lifecycle (автоматизация)
Фоновый цикл в `main.py` каждую минуту:
1. Находит закрытые месяцы (граница: МСК последний день 23:59).
2. Архивирует месяц (`403_budget_archive_month.sql`).
3. Чистит active budget (`404_budget_active_clear_month.sql`).
4. Чистит active bills (`522_bills_clear_month.sql`).

Итог: закрытый месяц фиксируется в archive-таблицах, active-таблицы освобождаются.

## 10) Shell backup (`scripts/create_backup.sh`)
Делает:
- `pg_dump -Fc` из контейнера db,
- `project.tgz` с исключениями (venv, backups, .git, кэши и т.п.),
- `meta.txt` и `checksums.sha256`,
- pruning старых backup-директорий по retention.

## 11) Поток запроса (от кнопки до БД)
1. Router -> handler.
2. Handler берет SQL-текст из `sql_cache` по пути.
3. `bind_named_params()` меняет `:name` на `$1..$N`.
4. `Database` выполняет query через asyncpg.
5. Handler форматирует ответ и отправляет в Telegram.

## 12) Текущие ограничения
- Редактирование/удаление уже созданной транзакции через UI отсутствует (делается SQL-правкой).
- UX-команды и SQL плотно связаны в одном большом файле `mvp.py` (~1900 строк).
- В репозитории пока нет зафиксированных коммитов (`git status` показывает весь проект как untracked).

## 13) Быстрый онбординг
1. Прочитать `bot/app/main.py`.
2. Прочитать `bot/app/handlers/menu.py`.
3. Прочитать `bot/app/handlers/mvp.py` по блокам: wizard -> budget -> planning -> stats/archive -> backup.
4. Просмотреть SQL-папки в порядке `20 -> 30 -> 40 -> 50 -> 90`.
5. Проверить `.env`, `docker-compose.yaml`, `scripts/create_backup.sh`.
