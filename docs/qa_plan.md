# План обеспечения качества (QA)

## Контекст
- Backend: FastAPI + PostgreSQL, медиасервис `/api/v1/media/*`, AI-пайплайн YOLO/CLIP (есть фолбэк), таблицы upload history/AI review.
- Mobile: Android (Kotlin, Jetpack Compose, MVVM), экраны Items/Locations/Quick Add/AI Review/Settings, AnalyticsLogger → `/api/v1/logs`.
- Инфра: Docker-compose (api + postgres + CIFS volume на NAS), alembic миграции.

## Текущее состояние
- Юнит-тесты backend: не запускались в этой сессии; последний зафиксированный результат 13/13.
- Юнит-тесты mobile: не запускались в этой сессии (есть `testDebugUnitTest`).
- Открытые дефекты см. `docs/defects.md` (DF-001, DF-002, DF-003, DF-005, DF-008).

## Основные риски качества
- Отсутствие проверок наличия YOLO весов на окружениях NAS → silent фолбэк.
- Видео-анализ даёт мало детекций на слабом железе (DF-002).
- Mobile AI Review не пишет review_log и не показывает ошибки сети → потери аудита.
- В docker-compose захардкожены CIFS креды NAS (DF-007) → риск утечки и невозможность безопасного CI.
- Нет интеграционных тестов на реальное `POST /media/upload` (фото/видео) и `/media/history`.

## Рекомендации по тестам
- Backend интеграционные (pytest + временные файлы):
  - `/media/upload` для JPG/PNG/HEIC/MP4: проверка размеров, mime, создания thumb, записи `MediaUploadHistory`, статуса AI (done/failed), сохранения hash.
  - `/media/history`: фильтр по owner_user_id/limit, наличие thumb_url/file_url.
  - Видео-анализ: проверка с разными `video_frame_stride`/`video_max_frames` и корректного progress в raw.
  - `/ai/detections/*`: accept/reject с валидными и невалидными `item_id`/`location_id` (ожидать 400/404), запись AIDetectionReview.
  - Фолбэк без YOLO/CLIP (моки импортов) → статус done + bbox-заглушка.
  - Файлы-фикстуры для тестов: `backend/app/tests/assets/sample.jpg`, `sample.heic`, `sample.mp4`.
- Mobile:
  - Инструментальные: AI Review (Queue/History) — загрузка списка, обработка ошибки сети, обновление после accept/reject.
  - Тест шаринга (Intent ACTION_SEND) для URL и PDF/изображения: создание item/receipt, навигация к ItemDetails.
  - Проверка UploadQueue: отображение статусов pending/retrying/failed.
- E2E (ручные/авто): снять фото на девайсе → загрузка → запись в history → AI Review показывает bbox → accept с привязкой к item → запись в детальную карточку.

## Чек-лист перед релизом
- ✅ `python -m pytest` в backend.
- ✅ `./gradlew testDebugUnitTest` в mobile (по возможности `connectedAndroidTest`).
- ✅ `alembic upgrade head` применён на окружении.
- ✅ YOLO веса скачаны или зафиксировано использование фолбэка (лог в /api/v1/logs).
- ✅ Нет открытых критических дефектов (P0/P1) или есть workaround в релиз-нотах.
- ✅ Docker-compose не содержит открытых секретов; `.env` заполнен.

## Инструменты и метрики
- Логи клиента: `/api/v1/logs` (добавить поля `user_id`, `device` при появлении auth).
- Health: `/api/v1/health/full` проверяет БД, доступность путей медиа и наличие YOLO весов (degraded, если чего-то нет).
- Метрики: время загрузки файла, время AI анализа, % failed детекций, доля HEIC/MP4 с ошибками.
- Регрессия: smoke-скрипт для API (`health`, upload photo, history) и Android UI чек-лист.

## Следующие действия QA
- Добавить тестовые файлы (JPG/HEIC/MP4 малого размера) в `backend/app/tests/assets` и покрыть сценарии upload/history.
- Наладить отчёт о дефектах/прогоне в `docs/defects.md` с обновлением статусов раз в спринт.
- Подготовить чек-лист ручного прогона AI Review (accept/reject/link) до появления автотестов.

## Чек-лист ручного прогона AI Review
- Загрузить фото через мобильный (Quick Add или карточка) → запись появляется в AI Review (Queue).
- Открыть детекцию, убедиться в наличии превью/меток → выполнить Accept (с item_id) → статус DONE, привязка к предмету.
- Создать/изменить привязку локации через Update Object → связанная локация отображается в ответе.
- Выполнить Reject без item/location → статус FAILED, запись в history и в AI Review исчезает из Queue.
- Проверить, что действия логируются (сервер: `aidetectionreview`, клиент: `/api/v1/logs` отправляет событие).
- В History (AI Review → History) виден результат с путём к файлу/превью и ai_status done/failed.
