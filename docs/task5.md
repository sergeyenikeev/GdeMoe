# Task 5 — История загрузок и AI-обработка (ГдеМоё)

## Что сделано
- Backend: добавлен журнал загрузок `mediauploadhistory` (миграция `0004_upload_history_and_ai_links`), эндпоинт `GET /api/v1/media/history`, ingestion клиентских логов `/api/v1/logs`, поддержка редактирования AI-объектов (`linked_item_id`, `linked_location_id`, PATCH `/api/v1/ai/objects/{id}`). Обновлено связывание AI-статусов в `/media/upload`, `/ai/*`.
- Mobile: AI Review получил вкладки Queue/History, предпросмотр фото/видео, статусы AI, форма редактирования привязок к предметам/локациям, отображение кандидатов; логирование AnalyticsLogger теперь уходит на backend. Добавлен DTO истории загрузок.
- Тесты/сборки: `python -m pytest` (13/13), `./gradlew testDebugUnitTest`, `./gradlew assembleDebug` — успешны.

## Что осталось/риски
- UI редактирования привязок сейчас вводит ID вручную; желательно автодополнение по списку предметов/локаций.
- Нет автоматических UI-тестов для нового экрана History; покрытие пока юнитами/ручной проверкой.
- Нужно прогнать `alembic upgrade head` на окружениях.
- Проверить совместимость с внешним AI-сервисом, если он используется (callback не проверялся).

## Как проверить
1) Backend: `cd backend && python -m pytest`.
2) Mobile: `cd mobile && ./gradlew testDebugUnitTest` и `./gradlew assembleDebug` (APK: `mobile/app/build/outputs/apk/debug/app-debug.apk`).
3) API: после `alembic upgrade head` вызвать `GET /api/v1/media/history` — увидеть статусы/превью. Патч объекта: `PATCH /api/v1/ai/objects/{id}` с `{"item_id":123,"location_id":5}`.
4) Мобильный: открыть вкладку AI → History, проверить превью, статусы, открыть видео, изменить привязки и убедиться в обновлении.

## Следующие шаги
- Добавить выбор предмета/локации через справочники вместо ручного ввода ID.
- Подтянуть логику синхронизации истории загрузок с локальным кешем (Room) для оффлайна.
- Дополнить CI проверкой новой миграции (alembic) и линтером Kotlin.
