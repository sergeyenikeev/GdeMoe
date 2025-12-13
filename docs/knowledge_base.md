# База знаний (Codex)

- Никогда не трогаем `notouch.txt`.
- Тесты: backend `cd backend && python -m pytest`; mobile `cd mobile && ./gradlew testDebugUnitTest`; сборка APK `./gradlew assembleDebug`.
- Миграции: новые изменения в БД выкатываем через `alembic upgrade head` (после добавления файла в `backend/alembic/versions`).
- Логи: на мобильном используем `AnalyticsLogger.event/debug/screen` — логи уходят в backend `/api/v1/logs` плюс в Logcat.
- Работа с AI: объекты детекции имеют `linked_item_id`/`linked_location_id`; редактирование через PATCH `/api/v1/ai/objects/{id}`.
- Журнал загрузок: `GET /api/v1/media/history` возвращает статус загрузки, превью, AI-резюме; модель `MediaUploadHistory`.
- Коммуникация с API: всегда дергать `ApiClient.sanitizeBaseUrl` перед созданием Retrofit клиента.
- Сохранение в git: перед коммитом — прогнать тесты, не добавлять чувствительные данные, не коммитить `notouch.txt`.
- Docker backend: перезапускать командой `cd backend/docker && docker compose build api && docker compose up -d api` (если есть орфаны — добавить `--remove-orphans`). После миграций обязательно `alembic upgrade head`.
