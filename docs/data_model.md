# Модель данных (PostgreSQL)

## ER-диаграмма (словами)
- users 1—N memberships — groups — workspaces
- workspaces 1—N locations (self-ref)
- workspaces 1—N items — N—N tags, groups, relations, media
- items 1—N history/notes
- media 1—N ai_detections — 1—N ai_detection_objects — N—N candidates(items)
- ai_detections 1—N ai_detection_reviews
- workspaces 1—N item_batches — items

## Основные таблицы
- users: id, email, password_hash, name, role, created_at
- workspaces: id, name, scope (private/public/group), owner_user_id, created_at
- locations: id, workspace_id, parent_id, name, kind (home/flat/room/closet/shelf/box/garage/other), path, meta, created_at
- items: id, workspace_id, owner_user_id, title, description, category, status, attributes JSONB, model, serial_number, purchase_date, price, currency, store, order_number/url, warranty_until, expiration_date, reminders JSONB, location_id, scope, batch_id, created_at/updated_at
- item_history: id, item_id, user_id, event_type, before JSONB, after JSONB, created_at
- item_notes: id, item_id, user_id, content, created_at, updated_at
- tags/item_tags: id, name; item_id+tag_id
- media: id, workspace_id, owner_user_id, location_id?, media_type (photo/video/document), path, thumb_path, mime_type, size_bytes, hash, created_at, analyzed_at
- item_media: item_id, media_id
- todos: id, workspace_id, item_id?, location_id?, title, description, status, due_date, created_at, updated_at
- item_batches: id, workspace_id, location_id?, title, created_by, created_at
- ai_detections: id, media_id, status, raw, created_at, completed_at
- ai_detection_objects: id, detection_id, label, confidence, bbox, suggested_location_id, decision, decided_by?, decided_at, created_at
- ai_detection_candidates: id, detection_object_id, item_id, score, created_at
- ai_detection_reviews: id, detection_id, user_id?, action, payload JSONB, created_at
- imports: id, workspace_id, user_id, source, status, stats JSONB, created_at

## Индексы/GIN
- GIN по items(description, attributes)
- B-Tree: items(status, location_id, purchase_date, warranty_until, expiration_date, price)
- GIN по tags.name (trigram)
- GIST/ltree по locations.path
- Индексы на media.hash и ai_detection.* по статусу

## Пути хранения медиа (NAS)
/data/gdemo/media/{workspace_id}/{user_id}/{item_id?}/file
Превью: /thumbs/, документы: /docs/.
