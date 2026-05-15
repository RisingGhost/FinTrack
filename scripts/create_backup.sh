#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_BASE_DIR="${1:-$ROOT_DIR/backups}"
BACKUP_LABEL="${2:-manual}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_DIR="$BACKUP_BASE_DIR/${TIMESTAMP}_${BACKUP_LABEL}"

mkdir -p "$TARGET_DIR"

DB_DUMP_PATH="$TARGET_DIR/db.dump"
PROJECT_ARCHIVE_PATH="$TARGET_DIR/project.tgz"
CHECKSUMS_PATH="$TARGET_DIR/checksums.sha256"
META_PATH="$TARGET_DIR/meta.txt"

echo "[backup] target dir: $TARGET_DIR"
echo "[backup] dumping database..."
docker compose exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DB_DUMP_PATH"

echo "[backup] packing project..."
tar -czf "$PROJECT_ARCHIVE_PATH" \
  --exclude='./.git' \
  --exclude='./backups' \
  --exclude='./Fin_tracker.venv' \
  --exclude='./.venv' \
  --exclude='./venv' \
  --exclude='./.DS_Store' \
  --exclude='./TZ_v1_finance_bot.pdf' \
  --exclude='./test.ipynb' \
  --exclude='./**/__pycache__' \
  --exclude='./**/*.pyc' \
  --exclude='./**/.pytest_cache' \
  --exclude='./**/.ipynb_checkpoints' \
  .

echo "[backup] writing metadata..."
{
  echo "timestamp=$TIMESTAMP"
  echo "label=$BACKUP_LABEL"
  echo "host=$(hostname)"
  echo "cwd=$ROOT_DIR"
  echo "retention_days=$RETENTION_DAYS"
} > "$META_PATH"

echo "[backup] checksums..."
(
  cd "$TARGET_DIR"
  sha256sum db.dump project.tgz meta.txt > checksums.sha256
)

echo "[backup] prune old backups (> ${RETENTION_DAYS} days)..."
find "$BACKUP_BASE_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

echo "[backup] done:"
du -h "$DB_DUMP_PATH" "$PROJECT_ARCHIVE_PATH" "$CHECKSUMS_PATH" "$META_PATH"
