# Сборка и запуск "ГдеМоё"

## Структура
- ackend/ — FastAPI + PostgreSQL + Alembic.
- ackend/docker/ — Dockerfile и docker-compose.
- mobile/ — Android (Kotlin, Jetpack Compose, MVVM).
- docs/ — документация.

## Backend локально (Python)
`ash
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
`
Проверка: curl http://localhost:8000/api/v1/health.

## Backend в Docker
`ash
cd backend/docker
copy ..\.env.example ..\.env  # проверьте пути к медиа
docker compose up -d --build
docker compose exec api alembic upgrade head
`

## Компиляция Python (опционально)
`ash
cd backend
pip install nuitka
nuitka --onefile --follow-imports app/main.py -o gdemoe-api
`

## Android
Требуется JDK 17, Android SDK, Gradle wrapper.
`ash
cd mobile
./gradlew assembleDebug   # или assembleRelease
`
APK: mobile/app/build/outputs/apk/debug/app-debug.apk (или release/app-release.apk).
Установка: db install -r app/build/outputs/apk/debug/app-debug.apk.

## Что проверить после обновления
1. pip install -r backend/requirements.txt (добавлен pillow-heif, opencv).
2. lembic upgrade head (новый статус in_progress для AI).
3. В приложении дать разрешения на камеру/микрофон, сделать фото/видео и убедиться, что AI-статус done и есть хотя бы один объект (фолбэк работает даже без YOLO).

## Рекомендации для съемки (MVP)
- Снимайте крупно один предмет, без лишнего фона, хорошее освещение.
- Не перекрывайте объект и держите в кадре целиком.
- Для видео — 2–3 секунды, медленно покачайте камерой вокруг предмета.
- Форматы: JPG/PNG/HEIC/MP4 поддерживаются; HEIC требует актуальных зависимостей (pillow-heif).
- Если веса YOLO не скачаны, сработает фолбэк-контур: будет одна рамка на крупный объект.

Android тесты:
- В каталоге mobile: `./gradlew testDebugUnitTest`
- UI/инструментальные (при наличии девайса): `./gradlew :app:connectedAndroidTest`
- Сборка APK: `./gradlew assembleDebug` (результат: mobile/app/build/outputs/apk/debug/app-debug.apk)
