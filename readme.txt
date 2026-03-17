GdeMoe

Приложение для домашнего учёта вещей с Android-клиентом и backend API.

Стек:
- Mobile: Android, Kotlin, Jetpack Compose, MVVM, Retrofit, Room.
- Backend: FastAPI, PostgreSQL, Alembic, Docker Compose.
- Медиа и распознавание: загрузка фото и видео, обработка через пайплайн детекции и review.

Основные возможности:
- Быстрое и массовое добавление вещей.
- Иерархия локаций: дом, комнаты, шкафы, коробки и другие уровни.
- Загрузка медиа с историей обработки и подтверждением найденных объектов.
- Экран review для проверки результатов распознавания и привязки к предметам и локациям.

Сборка и запуск:
- Mobile: `cd mobile && ./gradlew assembleDebug`
- Backend: `cd backend/docker && docker compose up -d --build`
- Миграции: `cd backend/docker && docker compose exec api alembic upgrade head`
- Health: `http://localhost:8000/api/v1/health`

Тесты:
- Mobile: `cd mobile && ./gradlew testDebugUnitTest`
- Backend: `cd backend && python -m pytest`

Документация:
- Сборка и локальный запуск: `docs/build_and_run.md`
- Архитектура: `docs/architecture.md`
- Модель данных: `docs/data_model.md`
- Описание продукта: `docs/project_description.md`
- Интеграция распознавания: `docs/ai_integration.md`
- Деплой backend на NAS: `docs/backend_deploy_on_nas.md`
- Релизный чек-лист: `docs/release_checklist.md`
