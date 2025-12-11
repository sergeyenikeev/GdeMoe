# Архитектура "ГдеМоё"

## Состав
- **Мобильное приложение (Android, Kotlin, Jetpack Compose, MVVM/Clean)**: работа офлайн/онлайн, Room-кэш, интеграция с backend, загрузка медиа, AI-инбокс.
- **Backend (FastAPI + PostgreSQL + Alembic)**: REST API, JWT, CRUD вещей/локаций/тегов/медиа, AI-интеграция, хранение на NAS.
- **Хранилище**: PostgreSQL; NAS/S3-совместимое хранилище для медиа; опционально Redis для кешей/очередей.
- **AI-пайплайн**: YOLO/CLIP (локально или внешний сервис) для детекции/классификации.
- **Docker**: сервисы api/db (и опционально redis/ai) в docker-compose.

## Потоки данных
1) Mobile → Backend: аутентификация, CRUD, загрузка медиа (presigned или прямой upload), запуск AI анализа.
2) Backend → NAS: сохранение оригинала и превью /data/gdemo/media/{workspace}/{user}/{item}/....
3) Backend ↔ AI: запрос на анализ (/ai/analyze), callback/чтение результатов, логирование решений пользователя.
4) Backend ↔ DB: транзакции через SQLAlchemy/Alembic, миграции версионируются.

## Основные сущности
- Users/Workspaces/Groups/Permissions
- Items/Locations/Tags/Todos/Media
- AI: AIDetection, AIDetectionObject, AIDetectionCandidate, AIDetectionReview
- ItemBatch для массового ввода

## Навигация мобильного приложения
Bottom bar: Вещи, Локации, Добавить, AI, Настройки. Экран AI — инбокс предложений. Быстрое добавление и батч-добавление вещей.

## Логирование и аналитика
- Backend: стандартный logging в основных AI-эндпоинтах.
- Mobile: AnalyticsLogger логирует экраны, клики, accept/reject и выбор локаций.
