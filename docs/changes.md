# История изменений

## 2025-12-28
- Backend: locations parent update/clear, location photo binding, upload history `location_id`, upload/AI `hint_item_ids`; Mobile: location editor + hint item IDs input.
- Backend: AI review logs пишутся с user_id из owner_user_id; добавлена валидация item/location; параметры видео `video_frame_stride`/`video_max_frames`; фильтры status/source для `/media/history`; нормализован progress видео-анализа.
- DevOps: docker-compose healthchecks, корректный `AI_YOLO_WEIGHTS_PATH`, обновлён `.env.example`, добавлен скрипт `scripts/deploy_nas.sh`.
- Документация: новый `docs/qa_report.md` и `docs/project_description.md`, обновлены `docs/system_plan.md`, `docs/devops_automation.md`, `docs/defects.md`, `docs/qa_plan.md`.

## 2025-12-15
- Data Science: полностью переписан `docs/data_science_plan.md` (ограничения пайплайна, цели, стек YOLO/RT-DETR + SAM-lite, CLIP/SigLIP + ANN, метрики, чек-лист задач).
- База знаний: добавлена ссылка на новый DS-план в `docs/knowledge_base.md` как точка входа для работ по моделям.
- Инструменты: добавлен скрипт `scripts/dataset_subset.py` для выборки подмножеств COCO/OpenImages с мэппингом классов и лицензиями.
- DS логистика: добавлены команды скачивания альтернативных датасетов (SKU-110K, RPC, GroZi-120) в план.
- Датасеты: добавлен документ `docs/datasets_download.md` (PowerShell команды: COCO, Open Images через Kaggle, RPC/SKU110K/GroZi).
- Data prep: добавлены конвертеры `scripts/convert_rpc_manifest.py`, `scripts/convert_sku110k_manifest.py`, `scripts/convert_yolo_manifest.py`; bbox в manifest теперь сохраняется как xyxy для COCO.
- Data prep: добавлен `scripts/build_yolo_dataset.py` для сборки unified YOLO датасета из manifest CSV.
- Training: добавлен `scripts/train_yolo.py` и настройка `AI_YOLO_WEIGHTS_PATH` для загрузки новых весов в backend.

## 2025-12-13
- Backend: добавлен журнал загрузок `mediauploadhistory` (миграция `0004_upload_history_and_ai_links`), новый `GET /api/v1/media/history`, ingestion клиентских логов `/api/v1/logs`, поддержка редактирования AI-объектов (`linked_item_id`, `linked_location_id`, PATCH `/api/v1/ai/objects/{id}`), обновлено связывание AI в media/items.
- Mobile: AI Review теперь с вкладками Queue/History, предпросмотром фото/видео, отображением статусов AI и редактированием привязок item/location; новый DTO UploadHistoryEntry; AnalyticsLogger шлет логи на backend.
- Тесты/сборки: `python -m pytest` (13/13), `./gradlew testDebugUnitTest`, `./gradlew assembleDebug` успешно.
- DevOps/безопасность: docker-compose берет NAS креды из `.env` (`NAS_USER`/`NAS_PASSWORD`); добавлен `/api/v1/health/full` (DB, медиа-пути, YOLO веса), обновлены инструкции по сборке/деплою и релизный чек-лист.
- Mobile settings: проверка подключения теперь использует `/api/v1/health/full` и показывает детали checks.
- Data Science: добавлен план развития моделей и автопривязки (`docs/data_science_plan.md`), отражён в базе знаний.
- Video AI: сохраняется прогресс по кадрам в `aidetection.raw` и создаются кандидаты на основе предметов из локации (AIDetectionCandidate) при анализе видео.
- OPS: добавлен документ `docs/ops_recommendations.md` с рекомендациями по развёртыванию/мониторингу.
- Dockerfile прогревает YOLO веса (`yolov8n.pt`) при сборке, чтобы избежать фолбэка "object".

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
