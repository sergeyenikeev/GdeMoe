# OPS рекомендации и развёртывание

## Развёртывание
- Backend: `cd backend/docker && docker compose up -d --build` (после заполнения `.env` с `POSTGRES_*`, `JWT_SECRET_KEY`, `NAS_USER`, `NAS_PASSWORD`). Миграции: `docker compose exec api alembic upgrade head`.
- Health: `/api/v1/health` (базовый), `/api/v1/health/full` (БД, пути медиа, YOLO веса). Добавьте healthcheck для контейнера api в compose.
- NAS: убедиться, что CIFS-толмаунты доступны: `/data/gdemo/public_media`, `/data/gdemo/private_media`; права 0777 или UID/GID контейнера. В `backend/docker/.env` заполнить `NAS_HOST`, `NAS_USER`, `NAS_PASSWORD` для корректного монтирования.
- Mobile: сборка `./gradlew assembleDebug` (или Release с подписью) для распространения apk.
- YOLO веса: Dockerfile теперь прогревает `yolov8n.pt` на этапе сборки. При смене версии весов — пересобрать образ или скопировать файл в `/root/.cache/ultralytics/assets/`.

## Обслуживание и мониторинг
- Логи: backend стандартный вывод + `/api/v1/logs` от мобильного клиента. Настройте ротацию (logrotate или docker logging driver).
- Метрики (минимум): время загрузки медиа, доля FAILED AI, наличие YOLO весов (health/full). План: добавить Prometheus endpoint.
- Бэкапы: `pg_dump` по расписанию; снимки NAS томов (public/private_media) или rsync на отдельный диск. Проверять размер и целостность.
- Алерты: падение health/full, рост FAILED детекций, отсутствие доступа к NAS (health full покажет `media_paths` = false).

## Рекомендации для разработки
- Всегда запускать тесты: backend `python -m pytest`; mobile `./gradlew testDebugUnitTest`; обновлять миграции `alembic upgrade head`.
- Не хранить секреты в репозитории; использовать `.env` и секреты CI.
- Проверять `/api/v1/health/full` после обновлений зависимостей (Pillow/torch/opencv/YOLO веса).
- Использовать тестовые фикстуры `backend/app/tests/assets` для быстрой проверки upload/history.
