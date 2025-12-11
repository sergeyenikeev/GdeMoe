# AI-интеграция "ГдеМоё"

## Общая схема
1. Клиент загружает фото/видео через /api/v1/media/upload, получает media_id.
2. Клиент вызывает POST /api/v1/ai/analyze с media_id (или /analyze_video для видео) — создаётся запись idetection со статусом pending.
3. Локальный пайплайн (YOLO/CLIP) или внешний AI-сервис обрабатывает медиа и добавляет idetectionobject и idetectioncandidate.
4. Клиент получает инбокс через GET /api/v1/ai/detections?status=pending.
5. Пользователь подтверждает/отклоняет: POST /api/v1/ai/detections/{id}/accept|reject, действия пишутся в idetectionreview.

## Пример запросов
- Запуск анализа:
`
POST /api/v1/ai/analyze
{ "media_id": 123 }
`
- Инбокс:
`
GET /api/v1/ai/detections?status=pending
`
- Принятие/отклонение:
`
POST /api/v1/ai/detections/10/accept
{ "item_id": 5, "location_id": 8 }
`
`
POST /api/v1/ai/detections/10/reject
{}
`
- Лог действия:
`
POST /api/v1/ai/detections/10/review_log
{ "action": "link_existing", "payload": {"item_id":5} }
`

## Модели (коротко)
- idetection: id, media_id, status (pending/in_progress/done/failed), created_at/completed_at, media_path/thumb_path.
- idetectionobject: label, confidence, bbox, suggested_location_id, decision (pending/accepted/rejected).
- idetectioncandidate: detection_object_id, item_id, score.
- idetectionreview: detection_id, user_id, action, payload, created_at.

## Связь с медиа
Файлы хранятся в /data/gdemo/media/{workspace}/{user}/{card_id}/...; thumb генерируется при загрузке. media_path и 	humb_path возвращаются в инбоксе для превью в мобильном приложении.
