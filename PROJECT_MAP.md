# Fin_Tracker — Project Map (актуально на 2026-05-15)

## 1) Snapshot
- Локальный путь: `/Users/boriskov/Documents/folder/Fin_Tracker`
- Прод-сервер: `/opt/fin_tracker`
- Стек: `Python 3.12`, `aiogram 3`, `asyncpg`, `PostgreSQL 16`, `Docker Compose`

## 2) Назначение проекта
Telegram-бот для личных финансов с упором на быстрый ввод операций и планирование по месяцам.

Основные блоки:
- учет `expense` и `income`;
- бюджет месяца (расходы + доходы);
- `Bills` как отдельный список регулярных платежей;
- архив закрытых месяцев;
- статистика по периодам;
- резервное копирование через Telegram-команду и shell-скрипт.

## 3) Корневая структура
- `README.md` — краткий гайд запуска под себя.
- `.gitignore` — исключения для секретов/бэкапов/venv.
- `docker-compose.yaml` — сервисы `db` + `bot`.
- `docker/Dockerfile` — образ бота.
- `bot/requirements.txt` — зависимости.
- `bot/app/main.py` — lifecycle приложения, polling, monthly archive loop.
- `bot/app/config.py` — валидация env.
- `bot/app/db/*` — DB pool, SQL-loader, bind named params.
- `bot/app/handlers/start.py` — `/start`.
- `bot/app/handlers/health.py` — `/health`.
- `bot/app/handlers/access.py` — whitelist middleware.
- `bot/app/handlers/menu.py` — все reply-кнопки.
- `bot/app/handlers/mvp.py` — основной продуктовый сценарий.
- `queries/*` — SQL-слои (`transactions`, `stats`, `budget`, `bills`, `admin`, `migrations`).
- `scripts/create_backup.sh` — shell backup (dump БД + tar проекта).

## 4) Runtime-архитектура
### 4.1 Docker сервисы
- `db`: `postgres:16`, healthcheck `pg_isready`.
- `bot`: Python-процесс `python -m app.main`.

### 4.2 Startup (`bot/app/main.py`)
1. `load_settings()` читает env.
2. Поднимается `asyncpg` pool (`min_size=1`, `max_size=5`).
3. SQL-файлы из `QUERIES_DIR` загружаются в in-memory cache.
4. Один раз вызывается `_archive_closed_months()`.
5. Стартует фоновой `_monthly_archive_loop()` (тик каждую минуту).
6. Запускается polling aiogram.

### 4.3 Shutdown
- отмена фоновой monthly-задачи;
- закрытие DB pool.

## 5) Конфигурация
Обязательные env:
- `TG_TOKEN`
- `TG_WHITELIST_TG_ID`
- `DATABASE_URL`
- `QUERIES_DIR`

Шаблон переменных: `.env.example`.

## 6) Модель данных (`fin` schema)
### 6.1 Справочники
- `expense_category(code)`
- `income_category(code)`

### 6.2 Транзакции
- `transactions`
  - `type`: `expense | income`;
  - `amount > 0`;
  - `occurred_at` (`timestamptz`);
  - `expense_category` и `income_category` взаимоисключающие;
  - `comment`, `created_at`.

### 6.3 Бюджет
- `budget_active(month_id, kind, category_code, amount, updated_at)`
- `budget_archive(month_id, kind, category_code, amount, archived_at)`
- `kind`: `expense_limit` или `income_plan`

### 6.4 Bills
- `bills(month_id, bill_name, planned_amount, is_active, ... )`
- `bills_archive(month_id, bill_name, planned_amount, archived_at)`

### 6.5 Технические логи
- `parse_error_log`.

## 7) SQL-слои
### `queries/20_transactions`
- insert expense/income;
- последние `N` операций;
- все операции месяца;
- duplicate-check;
- future-date warning.

### `queries/30_stats`
- totals/top categories/top items/clean income для `today|week|month|year|range`.
- `330_stats_year_totals.sql` учитывает перенос `last month`, чтобы не удваивать доход между месяцами.

### `queries/40_budget`
- active budget read/upsert;
- автокопия предыдущего месяца в новый (`402`);
- текущие срезы: remaining/progress/summary;
- архивные срезы: history_*;
- архивирование закрытого месяца (`403`);
- очистка active (`404`).

### `queries/50_bills`
- статус Bills по месяцу (active/archive);
- список bill names для picker;
- deactivate/upsert Bills;
- очистка Bills месяца.

### `queries/90_admin`
- health-check;
- QA сверочные запросы.

## 8) Telegram-функционал
### 8.1 Access
`WhitelistMiddleware` пускает только `TG_WHITELIST_TG_ID`. Иначе `Access denied`.

### 8.2 Главное меню
- `💰 Income`
- `💸 Expense`
- `🗓️ Planning`
- `🧾 Budget`
- `🕘 Recent operations`

### 8.3 Planning меню
- `📝 Bills`
- `🔄 All`
- `💰 Income`
- `💸 Expenses`
- `⬅ Back`

`/stats` и кнопка `🗓️ Planning` открывают это меню (это не “stats-экран”).

### 8.4 Budget меню
- `📌 Overview`
- `📉 Budget`
- `📈 Income`
- `📄 Bills`
- `🗂 Archive`
- `⬅ Back`

### 8.5 Last operations меню
- `📅 All this month`
- `25 operations`
- `15 operations`
- `⬅ Back`

### 8.6 Флоу добавления транзакции
Для `expense` и `income`:
1. сумма;
2. категория;
3. дата/время автоматически = `now` по МСК;
4. комментарий;
5. confirm.

Для расхода в категории `Bills`:
- бот предлагает выбрать bill кнопками из текущего списка `fin.bills`;
- добавляется fallback-значение `unexpected bill`.

### 8.7 Planning setup (bulk)
Формат ввода: `Name Amount` (также поддержаны `|`, `;`, ` - `, `:`).

Режимы:
- `📝 Bills`: редактирование списка Bills как текстового шаблона.
- `💰 Income`: редактирование income-плана.
- `💸 Expenses`: редактирование expense-плана (без категории `Bills`).
- `🔄 All`: последовательность `Expenses -> Income -> Bills`.

Поведение:
- бот сначала показывает текущий шаблон;
- пользователь правит текст и отправляет;
- бот валидирует и сохраняет.

### 8.8 Budget/Stats/Archive
- `/budget` (`Overview`) показывает:
  - таблицу расходного бюджета (`Planned`, `Diff`),
  - таблицу доходов (`Actual`, `Expected`),
  - строку `Clean income`,
  - `I/O balance now/exp`.
- Быстрые slash-статы: `/today`, `/week`, `/month`, `/year`.
- Архив открывается из `Budget -> 🗂 Archive`, затем месяц кнопкой.

### 8.9 Backup в Telegram
`/backup` формирует JSON и отправляет документом:
- transactions (до 50000 последних),
- budget active/archive,
- bills active/archive.

## 9) Автоархивация месяца
Фоновый цикл в `main.py` каждую минуту:
1. ищет “закрытые” месяцы по МСК (граница: последний день 23:59);
2. переносит данные в архив (`403_budget_archive_month.sql`);
3. чистит `budget_active` (`404_budget_active_clear_month.sql`);
4. чистит `bills` текущего месяца (`522_bills_clear_month.sql`).

## 10) Backup и переносимость
### 10.1 Shell backup (`scripts/create_backup.sh`)
Делает:
- `pg_dump -Fc` из контейнера БД;
- `project.tgz`;
- `meta.txt`, `checksums.sha256`;
- cleanup старых backup-папок по retention.

### 10.2 Portable backup
Проверен сценарий “снять на сервере -> поднять локально” через:
- archive с образами/volume/dump/source/meta;
- проверка checksum;
- восстановление в отдельный compose-проект.

## 11) Важные ограничения
- UI-редактирования/удаления конкретной транзакции пока нет (делается SQL-операцией по `id`).
- `mvp.py` крупный (много бизнес-логики в одном файле).
- Ветка `main` локально без коммитов (первичная инициализация репозитория еще не выполнена).

## 12) Публикация в Git (текущее состояние)
- `.gitignore` уже добавлен.
- В публичный репозиторий нельзя включать `.env`, `backups/`, dump-файлы.
- Если секреты когда-либо были в истории/архивах, их нужно ротировать (`TG_TOKEN`, DB password).

## 13) Быстрый онбординг
1. `README.md`
2. `bot/app/main.py`
3. `bot/app/handlers/menu.py`
4. `bot/app/handlers/mvp.py`
5. `queries/20 -> 30 -> 40 -> 50 -> 90`
6. `docker-compose.yaml`, `scripts/create_backup.sh`
