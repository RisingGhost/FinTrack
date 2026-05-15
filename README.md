# Fin Tracker Bot

Telegram-бот для учета личных финансов: доходы, расходы, бюджет, Bills (регулярные платежи), архив по месяцам и базовая аналитика.

## Что умеет
- Быстрое добавление `income` и `expense` через кнопки и wizard.
- Планирование бюджета на месяц:
  - лимиты расходов,
  - план доходов,
  - список Bills.
- Просмотр текущего бюджета и архива месяцев.
- Последние операции и периодическая статистика.
- Автоархивация закрытого месяца по МСК (в конце месяца).

## Стек
- Python 3.12
- aiogram 3
- asyncpg
- PostgreSQL 16
- Docker / Docker Compose

## Быстрый старт под себя
1. Подготовьте `.env`:

```bash
cp .env.example .env
```

2. Заполните в `.env` свои значения:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `TG_TOKEN`
- `TG_WHITELIST_TG_ID`

3. Запустите сервисы:

```bash
docker compose up -d --build
```

4. Если БД новая, инициализируйте схему вручную (в проекте нет автозапуска миграций):

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < queries/00_migrations/001_init_schema.sql
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < queries/00_migrations/002_add_bills_archive.sql
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < queries/00_migrations/003_normalize_income_codes.sql
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < queries/10_seed/010_seed_categories.sql
```

5. Проверьте логи бота:

```bash
docker compose logs -f bot
```

## Полезные команды
- `docker compose ps`
- `docker compose restart bot`
- `docker compose logs -f db`
- `docker compose down`

## Основные команды в Telegram
- `/start`, `/help`, `/health`
- `/income`, `/expense`
- `/budget`, `/budget_income`, `/budget_expense`, `/bills`
- `/last`, `/today`, `/week`, `/month`, `/year`
- `/backup`

## Структура проекта
- `bot/app/main.py` — lifecycle приложения, polling, monthly archive loop.
- `bot/app/handlers/mvp.py` — основной пользовательский сценарий.
- `bot/app/db/*` — пул БД, SQL-loader, binding параметров.
- `queries/*` — SQL по доменам (`transactions`, `budget`, `bills`, `stats`, `admin`).
- `scripts/create_backup.sh` — shell backup (проект + dump БД).

## Важно по безопасности
- Не коммитьте `.env` и `backups/`.
- Перед публичным репозиторием используйте только `.env.example`.
- Если токен случайно утек, перевыпустите его через BotFather.

