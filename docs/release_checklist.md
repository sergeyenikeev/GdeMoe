# Release checklist (ГдеМоё)

## Перед сборкой
- Обновить `.env` и секреты: `JWT_SECRET_KEY`, `POSTGRES_*`, `AI_SERVICE_URL` (если внешний), `NAS_USER`/`NAS_PASSWORD`.
- Применить миграции локально: `cd backend && alembic upgrade head`.
- Прогнать тесты: backend `python -m pytest`; mobile `./gradlew testDebugUnitTest` (и `:app:connectedAndroidTest` при девайсе).

## Сборка и артефакты
- Backend: при необходимости `docker compose build api` (или Nuitka-сборка).
- Mobile: `./gradlew assembleDebug` или `assembleRelease` (с подписью); сохранить APK как артефакт.

## Проверки после выката
- Health: `curl /api/v1/health` (и `/api/v1/health/full`, если добавлен).
- БД/миграции: `docker compose exec api alembic current` показывает head.
- NAS: каталоги `/data/gdemo/public_media` и `/data/gdemo/private_media` смонтированы, записи создаются.
- AI: YOLO веса доступны или фолбэк включён; выполнить тестовый upload (JPG) → статус AI `done` в `GET /api/v1/media/history`.
- Логи: `/api/v1/logs` принимает записи от клиента; ошибки отсутствуют.

## Релизные заметки
- Зафиксировать известные дефекты из `docs/defects.md` (особенно Monitoring/Открытые).
- Описать ограничения: если AI работает во фолбэке, упомянуть сниженное качество; при отсутствии UI-автодополнения для AI Review — указать ввод ID.
