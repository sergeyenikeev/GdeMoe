# Деплой backend на NAS Terramaster F2-212

## Предусловия
- Установлен Docker и docker-compose на NAS.
- Свободное место под медиа: /data/gdemo/public_media, /data/gdemo/private_media.
- Порты: 8000 (API), 5432 (PostgreSQL) открыты во внутренней сети.

## Шаги
1) Скопировать проект на NAS (например, через SCP) в каталог /volume1/gdemo.
2) Перейти в ackend/docker и создать .env из .env.example; при необходимости скорректировать MEDIA_PUBLIC_PATH и MEDIA_PRIVATE_PATH на NAS.
3) Запустить контейнеры:
`ash
cd /volume1/gdemo/backend/docker
docker compose up -d --build
`
4) Применить миграции:
`ash
docker compose exec api alembic upgrade head
`
5) Проверить API:
`ash
curl http://<NAS_IP>:8000/api/v1/health
`
6) Убедиться, что каталоги медиа созданы и доступны контейнеру: /data/gdemo/public_media, /data/gdemo/private_media.

## Обновление
- При обновлении зависимостей выполнить: docker compose build api && docker compose up -d.
- При изменении схемы БД повторить lembic upgrade head.

## Особенности AI
- Если нет интернета на NAS, YOLO может не скачать веса; фолбэк-детекция включена (контуры/рамка), статус будет done, но результаты ограничены.
- Для лучшего качества загрузите ~/.cache/ultralytics/assets/yolov8n.pt внутрь контейнера или на хост.
