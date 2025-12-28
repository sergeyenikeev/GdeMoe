# План улучшения моделей распознавания (AI/ML)

## Текущее состояние
- Детекция: легкая обертка над YOLOv8n в `backend/app/services/ai/detector.py` с заглушкой; веса ищутся только в `~/.cache/ultralytics/assets/yolov8n.pt`, дообучения под домен нет, сегментации нет.
- Фичи: CLIP (`embeddings.py`) считается только для кропов bbox; нет текстовых эмбеддингов карточек, нет стораджа признаков/ANN индекса.
- Видео: выборка кадров в `video.py` фиксированным `frame_stride=180`, `max_frames=3`; нет трекинга/адаптивной выборки, сырая мета в `aidetection.raw`.
- Матчинг: кандидаты подбираются по последним `Item` в той же локации; нет приоритета по описанию/тегам, нет негативных примеров.
- Контроль: нет метрик AP/AR, top-k match, latency/CPU профиля; raw/логи не стандартизированы.

## Цели апгрейда
1) Стабильное распознавание объектов и их положения на фото/видео на CPU/NAS.  
2) Автоматическая привязка к карточкам и локациям (re-ranking по контексту).  
3) Метрики качества и регрессионные проверки перед релизом.  

## Предлагаемый стек
### Детекция и сегментация
- Базовая модель: YOLOv8s/YOLO11n или RT-DETR-R18 с дообучением на доменных данных (фото вещей/полок/коробок). Экспорт ONNX INT8 для NAS + GPU/CPU профили.
- Локализация сцены: компактная модель классов `shelf/box/closet/room/table/floor/hand/other` + `bbox_quality` (occlusion/blur) для подсказок UI.
- Точные кропы: SAM-lite или YOLO-seg для уточнения масок → лучше эмбеддинги и подсветка.
- Видео: ByteTrack/OC-SORT поверх детектора, адаптивный stride (1 кадр/с при движении, 1 кадр/3–5 с при статике), ранняя остановка при повторяющихся кадрах.

### Эмбеддинги и матчинг карточек/локаций
- Эмбеддинги изображений: CLIP ViT-B/16 или SigLIP-SO400M (если есть CUDA) + квантованная ONNX-версия для CPU. Хранить кропы в ANN (faiss/hnswlib).
- Текстовые эмбеддинги карточек: title + tags + category + location_path; пересчет при изменении карточки или по cron, хранить в том же пространстве.
- Candidate generator: top-K по CLIP сходству (crop→items) с re-rank по совпадению локации, категории, свежести карточки и prior на локации пользователя.
- Сохранять в `AIDetectionCandidate` поля `source` (`clip|location_prior|recent_item`), `score` для объяснимости в UI.

### Архитектура сервиса
- Вынести тяжелый инференс в отдельный контейнер (`ai_service_url`) с очередью (Redis/RQ или Celery), чтобы API не падало без torch/ultralytics.
- Версионировать веса/препроцессинг (`model_version`, `preprocess_version`) и писать их в `aidetection.raw` + `/api/v1/health/full`.
- Общий модуль препроцессинга (resize/normalize/letterbox) + фиксированные seed/детерминизм.

## Данные и разметка
- Источники: существующие медиа (`media.path`), `sample.jpg`, будущие пользовательские загрузки (с opt-in). Фильтрация по MIME/blur/histogram для чистоты.
- Разметка: Label Studio/CVAT, классы `{item, box, shelf, closet, bag, hand, document, background}`, класс сцены (room/closet/garage/other); для видео — keyframes + треки.
- Сплит: train/val/test по workspace/user (без утечек), ≥15% валидации. Версионировать в DVC/облаке.
- Аугментации: шум/низкий свет, motion blur, crop&shift, mixup/cutout для мелких предметов.
- Negative mining: кадры без целевых объектов и конфликтные пары (похожие на разные карточки) для улучшения re-ranking.

## Метрики и контроль качества
- Детекция: mAP50-95, recall@0.5, latency p50/p95 на CPU и GPU, RAM/VRAM.
- Матчинг: top-1/3/5 crop→item accuracy, MAP@5 по локации, precision/recall кандидатов.
- Видео: recall по трекам, % пропущенных сцен при адаптивном stride, время на минуту видео.
- SLO: фото ≤1.2 c (CPU), видео 30–60 c на минуту материала (CPU); деградации >5% блокируют релиз.

## План работ (контроль)
- [ ] Сбор датасета: выгрузка медиа, фильтр по качеству, подготовка списка к разметке (DS).
- [ ] Разметка пилота 1k кадров (bbox + scene class), настройка DVC/Label Studio (DS/QA).
- [ ] Дообучение детектора (YOLO11n/RT-DETR) + экспорт ONNX/INT8, бенчмарк на NAS/CPU (DS).
- [ ] Внедрение ANN индекса эмбеддингов кропов + текстовые эмбеддинги карточек, генерация кандидатов (BE/DS).
- [ ] Улучшение видео пайплайна: ByteTrack, адаптивный stride, логирование прогресса в `raw` (BE).
- [ ] Метрики и health: записи в `aidetection.raw.metrics`, расширение `/api/v1/health/full` (BE).
- [ ] E2E регрессия: upload → analyze → review → accept на сэмплах из `backend/app/tests/assets/` (QA).

## Риски и зависимости
- Torch/ONNX на NAS: собрать образ с нужными версиями, держать fallback детектор.
- Права на данные: consent на использование пользовательских медиа; обезличивание метаданных.
- Отсутствие GPU: приоритет маленькие модели + квантование; предусмотреть деградационный режим.

## Исполнение: спринт 0 (старт)
- [В прогрессе] Сбор датасета: сформировать выгрузку файлов для разметки (MIME: jpg/png/heic/mp4) с метой `workspace_id`, `location_id`, `created_at`; исключить дубликаты по hash (подготовить SQL/скрипт, owner DS).
- [В прогрессе] ТЗ на разметку: класс-сетка `{item, box, shelf, closet, bag, hand, document, background}` + scene-class; примеры положительные/отрицательные, требование к bbox/маскам (owner DS/QA).
- [ToDo] Развернуть Label Studio/CVAT (docker-compose) и подключить storage с выборкой из шага 1.
- [Готово] Скрипт выборки внешних датасетов: `scripts/dataset_subset.py` — вытягивает подмножество COCO/OpenImages с мэппингом классов и лицензиями в манифест CSV (опционально копирует картинки для COCO).
- [ToDo] Бенчмарк моделей: собрать baseline YOLOv8n vs YOLO11n/RT-DETR (ONNX fp16/int8) на 50-100 изображениях, замер latency p50/p95 CPU.
- [ToDo] ANN-прототип: выбрать faiss/hnswlib, прогнать эмбеддинги существующих кропов (tests/assets + пилот) и карточек (title+tags) → top-K выдача, схема `AIDetectionCandidate`.
- [ToDo] Видео пайплайн: дизайн адаптивного stride + ByteTrack/OC-SORT, формат прогресса в `aidetection.raw` (progress, frame_stride, frames_total, tracker info).
- [ToDo] Метрики/health: формат `aidetection.raw.metrics` (mAP/recall/latency), расширение `/api/v1/health/full` проверкой наличия весов и версии препроцессинга.
- [Готово] Внешние датасеты без GCP billing: SKU-110K, RPC, GroZi-120 — скачаны и распакованы локально.
- [Готово] Конвертация датасетов в единый manifest (bbox xyxy): COCO/RPC/SKU/GroZi → `D:/tmp/ds_all/manifest_train.csv`, `D:/tmp/ds_all/manifest_val.csv` (merge через `scripts/merge_manifests.py`).
- [ToDo] Сборка unified YOLO датасета: `scripts/build_yolo_dataset.py` (hardlink/copy в `images/`, генерация `labels/`, `dataset.yaml`).
- [ToDo] Обучение базовой модели: `scripts/train_yolo.py` (Ultralytics), экспорт `best.pt` и настройка `AI_YOLO_WEIGHTS_PATH` на backend.
