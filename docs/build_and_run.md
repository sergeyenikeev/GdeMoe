# Сборка и запуск "ГдеМоё"

## Структура
- backend/ — FastAPI + PostgreSQL + Alembic.
- backend/docker/ — Dockerfile и docker-compose.
- mobile/ — Android (Kotlin, Jetpack Compose, MVVM).
- docs/ — документация.

## Backend локально (Python)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
set POSTGRES_HOST=localhost
set POSTGRES_DB=gdemoe
set POSTGRES_USER=gdemoe
set POSTGRES_PASSWORD=gdemoe
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
Проверка: `curl http://localhost:8000/api/v1/health`.

## Backend в Docker
```bash
cd backend/docker
copy ..\.env.example ..\.env  # при необходимости правим пути и секреты
docker compose up -d --build
docker compose exec api alembic upgrade head
```

## Упаковка Python (опционально)
```bash
cd backend
pip install nuitka
nuitka --onefile --follow-imports app/main.py -o gdemoe-api
```

## Android
Требуется JDK 17, Android SDK, Gradle wrapper.
```bash
cd mobile
./gradlew assembleDebug   # или assembleRelease
```
APK: `mobile/app/build/outputs/apk/debug/app-debug.apk` (release: `app-release.apk`).
Установка: `adb install -r app/build/outputs/apk/debug/app-debug.apk`.

## Порядок проверки новых фич загрузки
1. `pip install -r backend/requirements.txt` (есть pillow-heif, opencv).
2. `alembic upgrade head` (таблица upload_history и статусы AI).
3. На устройстве/эмуляторе загрузить фото/видео, убедиться, что статус AI доходит до `done`, превью доступно, а запись видна в `GET /api/v1/media/history`.

## Минимальные критерии для релиза (MVP)
- Backend отвечает и пишет в БД/хранилище, CI юнит-тесты зелёные.
- Мобильный клиент умеет добавить/просмотреть предметы, загрузить медиа и увидеть статус AI.
- Видео: до 2–3 минут, UI показывает прогресс/ошибку.
- Форматы: JPG/PNG/HEIC/MP4 поддержаны; HEIC читается через pillow-heif.
- Если YOLO не скачан, включается фолбэк-детекция, пользователю показываем статус failed/упрощённый результат.

Android проверки:
- Юнит: `./gradlew testDebugUnitTest`
- Инструментальные (при наличии девайса): `./gradlew :app:connectedAndroidTest`
- Сборка APK: `./gradlew assembleDebug`
