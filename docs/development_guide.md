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


Обзор стекa зависимостей

fastapi==0.115.5 – основной веб-фреймворк; роутинг, валидация, автодокументация (OpenAPI/Swagger) и асинхронные endpoint’ы с минимальными накладными расходами.
uvicorn[standard]==0.24.0.post1 – ASGI-сервер, запускает FastAPI-приложение и обеспечивает поддержку HTTP/2, WebSocket и многопоточность через стандартный набор расширений.
SQLAlchemy==2.0.23 – ORM/SQL toolkit для работы с базами данных: описывает модели, строит запросы, управляет сессиями и миграциями на уровне кода.
asyncpg==0.29.0 – высокопроизводительный асинхронный драйвер PostgreSQL, используемый SQLAlchemy (или напрямую) для неблокирующих запросов к базе.
alembic==1.13.1 – миграции схемы базы, нужны при изменении моделей SQLAlchemy, чтобы синхронизировать структуру PostgreSQL.
psycopg2-binary==2.9.9 – альтернативный драйвер PostgreSQL (сделан для синхронных задач); часто устанавливают, чтобы иметь запасной вариант или для инструментов, требующих psycopg2.
pydantic==2.5.2 – базовая валидация/сериализация данных (моделей запросов/ответов FastAPI) с поддержкой строгих типов и кастомных валидаторов.
pydantic-settings==2.1.0 – расширение Pydantic, которое организует конфигурацию приложения (из env-файлов, переменных окружения и т.п.) через декларативные классы.
python-multipart==0.0.6 – поддержка multipart/form-data, нужна FastAPI для приёма файлов и форм в запросах.
python-jose[cryptography]==3.3.0 – JWT-шифрование/дешифрование; используется для генерации и проверки токенов авторизации.
passlib[bcrypt]==1.7.4 – безопасное хеширование паролей (обычно bcrypt); позволяет хешировать, проверять и обновлять пароли пользователей.
python-dotenv==1.0.0 – загружает переменные окружения из .env, упрощая локальную разработку и настройку конфигурации.
Pillow==10.1.0 – базовая библиотека для работы с изображениями: открытие, преобразования, сохранение в разных форматах.
numpy==1.26.3 – численные операции и матричные/тензорные структуры, необходимость для многих ML/вспомогательных вычислений (например, при обработке изображений).
pillow-heif==0.16.0 – поддержка формата HEIC/HEIF через Pillow, если приложение принимает такие изображения.
opencv-python-headless==4.9.0.80 – компьютерное зрение без GUI, используется для обработки изображений/видео на сервере (фильтры, поиск контуров и т.п.).
torch==2.1.2+cpu – PyTorch-фреймворк для ML/нейросетей; здесь стоит CPU-версия для инференса моделей без GPU.
torchvision==0.16.2+cpu – вспомогательные утилиты для PyTorch: загрузка моделей, трансформации изображений, вспомогательные датасеты.
open_clip_torch==2.20.0 – реализация CLIP от OpenAI; позволяет получать эмбеддинги текста/изображений для поиска, рекомендаций, генерации caption и т.п.
ultralytics==8.0.227 – библиотека для работы с YOLO-моделями (детекция объектов) и утилиты тренировки/инференса.
email-validator==2.1.0.post1 – проверка формата почтового адреса (используется валидацией Pydantic).
httpx==0.26.0 – асинхронный HTTP-клиент для вызовов внешних API из сервиса (можно использовать вместо requests в асинхронных задачах).
aiofiles==23.2.1 – асинхронные файловые операции (чтение/запись) для работы с загруженными медиа, чтобы не блокировать событийный цикл.
pypdf==3.17.0 – чтение/манипуляции PDF (извлечение текста или метаданных), если сервис работает с документами.
aiosqlite==0.20.0 – асинхронный драйвер SQLite; может использоваться для тестов, кэширования или локального сохранения при необходимости.

API/HTTP

FastAPI стартует приложение, подключает роутеры и принимает UploadFile/File/Form, поэтому python-multipart нужен для парсинга multipart-запросов, а мы используем его прямо в media-маршрутах. citebackend/app/main.py:10-19backend/app/api/routes/media.py:16-100
uvicorn запускает ASGI-сервер и его логгер используется в main, а команды в Docker/Docker Compose запускают именно uvicorn app.main:app. citebackend/docker/Dockerfile:24backend/docker/docker-compose.yml:12backend/app/main.py:19
aiofiles сохраняет загрузки без блокировки (в API загрузки медиа и чеков). citebackend/app/api/routes/media.py:15,91-120backend/app/api/routes/imports.py:9,82-88
httpx делает асинхронные вызовы к внешнему AI-сервису и к веб-ресурсам в product_fetcher. citebackend/app/api/routes/ai.py:7,134-150backend/app/services/imports/product_fetcher.py:8,115
Конфигурация и безопасность

pydantic (BaseModel + EmailStr) вместе с email-validator проверяют email/password-пейлоады (LoginRequest). citebackend/app/schemas/auth.py:4-12
pydantic-settings настраивает Settings и python-dotenv обеспечивает чтение из .env без дополнительных шаблонов. citebackend/app/core/config.py:10-33
python-jose генерирует JWT в core/security, а passlib[bcrypt] хеширует/проверяет пароли в маршрутах auth. citebackend/app/core/security.py:6-30backend/app/api/routes/auth.py:8-63
База данных

SQLAlchemy описывает модели и предоставляет асинхронную сессию, а asyncpg — драйвер строк подключения postgresql+asyncpg. citebackend/app/db/session.py:1-14backend/app/models/user.py:1-46backend/app/core/config.py:103-114
alembic управляет миграциями (env.py настраивает SQLAlchemy URL, 0005… добавляет новые колонки), psycopg2-binary просто закреплён в requirements.txt для синхронных утилит, которые могут по‑прежнему требовать его. citebackend/alembic/env.py:1-38backend/alembic/versions/0005_location_photo_and_history_location.py:1-32backend/requirements.txt:1-26
aiosqlite используется в pytest-фикстуре для создания временной SQLite базы. citebackend/app/tests/conftest.py:7-26
Медиа и ИИ

Pillow делает миниатюры в media и загружает изображения для пайплайна, а pillow-heif регистрирует HEIF/HEIC-открыватели, чтобы использовать те же API. citebackend/app/api/routes/media.py:137-180backend/app/services/ai/pipeline.py:15-50
numpy работает с массивами изображений в пайплайне и fallback-детекторе (нормализация эмбеддингов, подсчёт контуров). citebackend/app/services/ai/pipeline.py:15-70backend/app/services/ai/detector.py:3-105
torch, open_clip_torch и torchvision подтягиваются в embeddings: open_clip.create_model_and_transforms возвращает preprocess, который опирается на torchvision, а сама модель инференсит через PyTorch. citebackend/app/services/ai/embeddings.py:12-66
ultralytics грузит YOLO-веса, а при их отсутствии или для видео/медиа API происходит fallback на opencv-python-headless (детекция контуров, кадры видео). citebackend/app/services/ai/detector.py:26-105backend/app/api/routes/media.py:163-179
pypdf извлекает текст из загружаемых чеков, чтобы можно было парсить суммы/магазины. citebackend/app/api/routes/imports.py:60-110

