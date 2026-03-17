# Руководство по разработке

Этот документ нужен как точка входа для человека, который впервые открывает проект и хочет быстро понять, где что находится и куда вносить изменения.

## Что за проект

GdeMoe состоит из двух основных частей:

- `backend/` — FastAPI API, работа с PostgreSQL, хранение медиа, AI-анализ и журнал review.
- `mobile/` — Android-клиент на Kotlin и Jetpack Compose.

Вокруг этого есть служебные папки:

- `docs/` — продуктовая, техническая и эксплуатационная документация.
- `scripts/` — утилиты для датасетов, обучения и деплоя.
- `.github/` — CI для тестов.

## Как устроен backend

Основной код живёт в `backend/app/`.

### Точки входа

- `backend/app/main.py` — старт FastAPI, подключение роутов, стартовые проверки окружения.
- `backend/app/core/config.py` — все настройки из `.env`: БД, пути к медиа, лимиты файлов, параметры видео-анализа, пути к весам YOLO.

### API-слой

- `backend/app/api/routes/` — HTTP-эндпоинты.
- `auth.py` — авторизация.
- `items.py` — CRUD по предметам.
- `locations.py` — дерево локаций и связанные операции.
- `media.py` — загрузка файлов, генерация превью, журнал загрузок, выдача медиа.
- `ai.py` — запуск анализа, AI Review, accept/reject/update_object.
- `imports.py` — импорт товаров и чеков.
- `health.py` — healthcheck и проверка зависимостей окружения.
- `logs.py` — приём клиентских логов с Android.

### Зависимости и БД

- `backend/app/api/deps.py` — общие зависимости FastAPI, включая текущую временную заглушку пользователя.
- `backend/app/db/session.py` — создание async engine и сессий SQLAlchemy.
- `backend/app/db/base.py` — импорт моделей для регистрации metadata и автогенерации миграций.

### Модели и схемы

- `backend/app/models/` — ORM-модели SQLAlchemy.
- `backend/app/schemas/` — Pydantic-схемы для API.

Обычно правило простое:

- если меняется таблица или структура хранения — правим `models/` и миграции;
- если меняется контракт API — правим `schemas/` и `api/routes/`;
- если меняется прикладная логика — чаще всего это `services/`.

### Сервисы

- `backend/app/services/ai/pipeline.py` — анализ изображений: детекция, эмбеддинги, подбор кандидатов.
- `backend/app/services/ai/video.py` — анализ видео через выборку кадров.
- `backend/app/services/ai/detector.py` — детектор объектов и фолбэк-режим.
- `backend/app/services/ai/embeddings.py` — расчёт эмбеддингов изображений.
- `backend/app/services/imports/product_fetcher.py` — вытаскивание данных по внешней ссылке на товар.

### Тесты

- `backend/app/tests/` — unit и integration тесты backend.
- `backend/app/tests/assets/` — небольшие тестовые файлы для upload и video.

Если меняете upload, AI, health или сериализацию, сначала смотрите существующие тесты рядом — они уже подсказывают ожидаемое поведение.

## Как устроен mobile

Основной код клиента живёт в `mobile/app/src/main/java/com/gdemo/`.

### Точки входа

- `MainActivity.kt` — запуск приложения и приём внешних share-intent.
- `ui/navigation/GdeNavHost.kt` — основной граф навигации и переходы между экранами.

### Слой данных

- `data/remote/ApiClient.kt` — сборка Retrofit-клиента.
- `data/remote/ApiService.kt` — все backend-эндпоинты в одном интерфейсе.
- `data/repository/` — тонкие репозитории поверх API.
- `data/model/` — DTO и модели клиента.
- `data/local/` — локальное хранение и настройки подключения.

### UI-слой

- `ui/screens/items/` — список предметов, карточка предмета, Quick Add.
- `ui/screens/locations/` — дерево локаций.
- `ui/screens/review/` — AI Review и история загрузок.
- `ui/screens/settings/` — настройки сервера и окружения.
- `ui/screens/search/` — поиск.
- `ui/theme/` — цвета, тема и типографика.

### Вспомогательные модули

- `util/AnalyticsLogger.kt` — отправка клиентских событий и отладочных логов на backend.
- `util/UploadQueue.kt` — очередь фоновых загрузок.

## Основные потоки данных

### 1. Загрузка фото или видео

Путь выглядит так:

1. Android вызывает `ApiService.uploadMedia`.
2. Backend принимает запрос в `backend/app/api/routes/media.py`.
3. Файл сохраняется на диск, при необходимости создаётся превью.
4. Создаётся запись `Media` и запись в `MediaUploadHistory`.
5. Если включён `analyze`, backend запускает `analyze_media` или `analyze_video`.
6. Результат анализа попадает в `AIDetection*` таблицы и дублируется в summary истории загрузок.

### 2. AI Review

1. Mobile запрашивает очередь через `ApiService.aiDetections`.
2. Backend собирает `AIDetection` вместе с объектами и кандидатами.
3. Пользователь делает accept/reject или редактирует объект.
4. Backend обновляет `AIDetection`, `AIDetectionObject`, `AIDetectionReview`.
5. Затем синхронизируется `MediaUploadHistory`, чтобы history на клиенте сразу показала актуальное состояние.

### 3. Импорт по ссылке или чеку

1. `MainActivity` принимает share-intent.
2. `GdeNavHost` решает, это ссылка или файл.
3. Для ссылки вызывается импорт товара, для файла — импорт чека.
4. После успешного импорта создаётся item и пользователь открывает его карточку.

## Куда смотреть, если нужно что-то изменить

### Если нужно добавить новый endpoint

- описать метод в `mobile/.../ApiService.kt`, если он нужен клиенту;
- реализовать маршрут в `backend/app/api/routes/`;
- при необходимости добавить или обновить `schemas/`;
- если меняется структура БД — добавить миграцию в `backend/alembic/versions/`.

### Если нужно поменять upload медиа

Смотрите в таком порядке:

- `backend/app/api/routes/media.py`
- `backend/app/services/ai/pipeline.py`
- `backend/app/services/ai/video.py`
- `mobile/app/src/main/java/com/gdemo/data/remote/ApiService.kt`
- `mobile/app/src/main/java/com/gdemo/ui/screens/items/QuickAddScreen.kt`

### Если нужно менять AI Review

Смотрите:

- `backend/app/api/routes/ai.py`
- `backend/app/models/ai.py`
- `mobile/.../data/repository/AiRepository.kt`
- `mobile/.../ui/screens/review/AiReviewViewModel.kt`
- `mobile/.../ui/screens/review/AiReviewScreen.kt`

### Если нужно добавить новое поле у сущности

Практически всегда меняются сразу несколько мест:

1. SQLAlchemy модель в `backend/app/models/`.
2. Миграция Alembic.
3. Pydantic-схема в `backend/app/schemas/`.
4. Retrofit DTO в `mobile/app/src/main/java/com/gdemo/data/model/`.
5. UI, если поле нужно показывать или редактировать.

## Практические правила для разработки

- Сначала смотрите, есть ли рядом похожий экран, endpoint или тест. В проекте уже много готовых паттернов.
- Если изменение затрагивает upload, AI или history, почти всегда нужно проверить и backend, и mobile.
- Если появилось новое поле в ответе API, не забывайте обновить DTO на Android.
- Если меняется поведение AI Review, важно не забыть про `MediaUploadHistory`, иначе history и очередь начнут расходиться.
- Если логика касается внешних файлов и NAS, сначала проверяйте `docs/backend_deploy_on_nas.md` и `docs/build_and_run.md`.

## С чего начать новому разработчику

Если хочется быстро войти в проект без долгого чтения, хороший маршрут такой:

1. `readme.txt`
2. `docs/architecture.md`
3. `docs/development_guide.md`
4. `backend/app/api/routes/media.py`
5. `backend/app/api/routes/ai.py`
6. `mobile/app/src/main/java/com/gdemo/ui/navigation/GdeNavHost.kt`
7. `mobile/app/src/main/java/com/gdemo/ui/screens/review/AiReviewScreen.kt`

После этого обычно уже понятно, как проходит основной пользовательский сценарий от загрузки медиа до подтверждения результата.
