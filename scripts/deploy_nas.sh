#!/usr/bin/env bash
set -euo pipefail

# Небольшой скрипт для ручного выката backend на NAS:
# поднимает контейнеры, прогоняет миграции и печатает health-статус.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend/docker"

if [[ ! -f "../.env" ]]; then
  echo "Missing backend/.env. Copy backend/.env.example and заполните настройки." >&2
  exit 1
fi

# Пересобираем и поднимаем сервисы, затем приводим схему БД к актуальному состоянию.
docker compose up -d --build
docker compose exec api alembic upgrade head

echo "Health checks:"
curl -fsS http://localhost:8000/api/v1/health > /dev/null
auth_status=$(curl -fsS http://localhost:8000/api/v1/health/full)
echo "$auth_status"
