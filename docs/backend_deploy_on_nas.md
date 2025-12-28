# Деплой backend на NAS Terramaster F2-212

## Предусловия
- Установлены Docker и docker-compose на NAS.
- Каталоги под медиа: `/data/gdemo/public_media`, `/data/gdemo/private_media` с правами на запись.
- Открыты порты 8000 (API) и 5432 (PostgreSQL) во внутренней сети.

## Шаги
1. Скопировать проект на NAS (например, `/volume1/gdemo`).
2. `cd backend/docker` и создать `.env` из `.env.example`; заполнить `POSTGRES_*`, `MEDIA_PUBLIC_PATH`, `MEDIA_PRIVATE_PATH`, а также `NAS_USER`/`NAS_PASSWORD` для CIFS.
3. Запустить контейнеры:
   ```bash
   cd /volume1/gdemo/backend/docker
   docker compose up -d --build
   ```
4. Применить миграции:
   ```bash
   docker compose exec api alembic upgrade head
   ```
5. Проверить API: `curl http://<NAS_IP>:8000/api/v1/health`.
6. Убедиться, что каталоги медиа доступны контейнеру: `/data/gdemo/public_media`, `/data/gdemo/private_media`.

## Обновление
- При изменении зависимостей: `docker compose build api && docker compose up -d`.
- При обновлении схемы БД — повторить `alembic upgrade head`.

## Особенности AI и хранения
- Если на NAS нет интернета и YOLO веса не скачаны, сработает фолбэк-детекция (контуры/одна рамка), статус `done` будет, но качество ограничено. Для полноценной работы загрузите `~/.cache/ultralytics/assets/yolov8n.pt` в контейнер/на хост.
- CIFS/пароли вынесены в `.env` переменные (`NAS_USER`/`NAS_PASSWORD`), не коммитить реальные значения в репозиторий.
