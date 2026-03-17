#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend/docker"

if [[ ! -f "../.env" ]]; then
  echo "Missing backend/.env. Copy backend/.env.example and ????????? ????????." >&2
  exit 1
fi

docker compose up -d --build
docker compose exec api alembic upgrade head

echo "Health checks:"
curl -fsS http://localhost:8000/api/v1/health > /dev/null
auth_status=$(curl -fsS http://localhost:8000/api/v1/health/full)
echo "$auth_status"
