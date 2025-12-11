GdeMoe — мобильное приложение и backend для поиска и учета вещей с ИИ-распознаванием.

Стек:
- Mobile: Android, Kotlin, Jetpack Compose, MVVM, Retrofit, Room.
- Backend: FastAPI, PostgreSQL, Alembic, Docker Compose; AI пайплайн YOLO/CLIP (опционально).

Сборка и запуск:
- Mobile: `cd mobile && ./gradlew assembleDebug` (APK: mobile/app/build/outputs/apk/debug/app-debug.apk).
- Backend (Docker): `cd backend/docker && docker compose up -d --build`, затем `docker compose exec api alembic upgrade head`.
- API health: http://localhost:8000/api/v1/health

AI-инбокс:
- Загрузка медиа `/api/v1/media/upload`, анализ `/api/v1/ai/analyze`, инбокс `/api/v1/ai/detections`, действия `/accept`, `/reject`, `/review_log`.

Навигация приложения:
- Bottom bar: Вещи, Локации, Добавить, AI, Настройки.
- Быстрое добавление: название, выбор/поиск локации, медиа; батч-добавление из локации.
- AI-review: список детекций с превью, Accept/Reject, переход к вещам-кандидатам.

Логи и аналитика:
- Основные действия пользователя и экраны логируются (AnalyticsLogger) для улучшения UX/UI.
- Backend AI endpoints логируются через стандартный logging.

Тесты:
- Mobile юнит-тесты: `cd mobile && ./gradlew testDebugUnitTest`.
- Перед пушем в GitHub прогонять тесты и проверять отсутствие секретов в репозитории.
