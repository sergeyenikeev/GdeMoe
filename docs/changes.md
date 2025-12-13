# История изменений

## 2025-12-13
- Backend: добавлен журнал загрузок `mediauploadhistory` (миграция `0004_upload_history_and_ai_links`), новый `GET /api/v1/media/history`, ingestion клиентских логов `/api/v1/logs`, поддержка редактирования AI-объектов (`linked_item_id`, `linked_location_id`, PATCH `/api/v1/ai/objects/{id}`), обновлено связывание AI в media/items.
- Mobile: AI Review теперь с вкладками Queue/History, предпросмотром фото/видео, отображением статусов AI и редактированием привязок item/location; новый DTO UploadHistoryEntry; AnalyticsLogger шлет логи на backend.
- Тесты/сборки: `python -m pytest` (13/13), `./gradlew testDebugUnitTest`, `./gradlew assembleDebug` успешно.

## 2025-12-12
- Backend: Pydantic схемы переведены на `ConfigDict(from_attributes=True)` (ai.py, item.py, location.py, user.py) для корректного ORM-маппинга.
- Mobile: стабильность `GdeNavHost` (убраны `!!`, добавлены safe-call), улучшен `ItemDetailsScreen` (статусы, dropdown), мелкие UI улучшения.
- Проверки: `python -m pytest` (backend 10 тестов), `./gradlew testDebugUnitTest`, `./gradlew assembleDebug`.
- Docker: `docker compose -f backend/docker/docker-compose.yml build` пересобран API.
- Синхронизация: подтянуты изменения с `origin/main` (sergeyenikeev/GdeMoe).

## 2025-12-11
- Обновлены маршруты аутентификации (refresh token), плейсхолдер ai service url в конфиге.
- Дополнен README, расширен AnalyticsLogger на фронте и бэке.
- Настроен GitHub Actions для юнит-тестов при push/PR (`.github/workflows/ci.yml`).

## 2025-12-10
- Quick Add и AI Review: улучшены загрузка превью, фильтры, поддержка media_path, review_log.
- Обновлены схемы ответов AI; UX-батчи (item_batches, ai_detection_reviews).

## 2025-12-09
- Рефактор списка предметов и поиска; intent-обработчики на мобильном.
- Backend: единая работа с item/media, парсинг PDF/HEIC, интеграция YOLO.
