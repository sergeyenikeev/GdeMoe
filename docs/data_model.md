# Модель данных (PostgreSQL)

## Текстовая ER-диаграмма
- users (1) — (N) memberships — (N) groups — (N) workspaces
- users (1) — (N) auth_tokens
- workspaces (1) — (N) locations (дерево self-reference)
- workspaces (1) — (N) items — (N) item_media — (N) media
- items (1) — (N) item_notes
- items (1) — (N) item_history
- items (N) — (N) tags через item_tags
- items (N) — (N) groups через group_items
- items (N) — (N) parent/child через item_relations (self-reference)
- locations (1) — (N) location_history
- workspaces (1) — (N) todos
- media (1) — (N) ai_detections (распознанные объекты)
- ai_detections (N) — (1) items (optional), (N) — (N) ai_detection_candidates (item candidates)

## Таблицы (ключевые поля)
- users: id PK, email UNIQUE, password_hash, name, role (admin/user), created_at.
- workspaces: id PK, name, scope (private/public/group), owner_user_id FK users, created_at.
- groups: id PK, workspace_id FK, name, parent_group_id FK nullable, settings JSONB.
- memberships: id PK, user_id FK, group_id FK, role (owner/editor/reader), created_at.
- auth_tokens: id PK, user_id FK, token, expires_at, created_at.
- locations: id PK, workspace_id FK, parent_id FK self, name, kind (enum: home/flat/room/closet/shelf/box/other), path ltree, meta JSONB, created_at.
- location_history: id PK, location_id FK, user_id FK, change JSONB, created_at.
- items: id PK, workspace_id FK, owner_user_id FK, title, description, category, status (enum), attributes JSONB, model, serial_number, purchase_date, price numeric(14,2), currency(3), store, order_number, order_url, warranty_until, expiration_date, reminders JSONB, location_id FK, scope, created_at, updated_at.
- item_history: id PK, item_id FK, user_id FK, event_type, before JSONB, after JSONB, created_at.
- item_notes: id PK, item_id FK, user_id FK, content TEXT, created_at, updated_at.
- tags: id PK, workspace_id FK, name UNIQUE(workspace_id,name), created_at.
- item_tags: item_id FK, tag_id FK, PRIMARY KEY(item_id, tag_id).
- item_relations: parent_item_id FK, child_item_id FK, PRIMARY KEY(parent_item_id, child_item_id).
- groups_items: group_id FK, item_id FK, PRIMARY KEY(group_id, item_id).
- media: id PK, workspace_id FK, owner_user_id FK, location_id FK nullable, media_type (photo/video/doc), path, thumb_path, mime_type, size_bytes, hash, created_at, analyzed_at nullable.
- item_media: item_id FK, media_id FK, PRIMARY KEY(item_id, media_id).
- todos: id PK, workspace_id FK, item_id FK nullable, location_id FK nullable, title, description, status (open/done), due_date, created_at, updated_at.
- ai_detections: id PK, media_id FK, status (pending/done/failed), raw JSONB, created_at, completed_at.
- ai_detection_objects: id PK, detection_id FK, label, confidence numeric, bbox JSONB, suggested_location_id FK nullable, created_at.
- ai_detection_candidates: id PK, detection_object_id FK, item_id FK, score numeric, created_at.
- imports: id PK, workspace_id FK, user_id FK, source (csv/email/api/photo), status, stats JSONB, created_at.

## Enum/справочники
- item_status: Новый, В порядке, Сломан, Потерян, Отремонтирован, Продан, Выкинут, Хочу купить, В пути, Надо проверить.
- location_kind: home, flat, room, closet, shelf, box, garage, other (расширяемо).
- todo_status: open, done.
- media_type: photo, video, document.
- scope: private, public, group.
- ai_detection_status: pending, done, failed.

## Индексы (ключевые)
- GIN на items(description, attributes) для полнотекста.
- B-Tree на items(status), items(location_id), items(purchase_date), items(warranty_until), items(expiration_date), items(price).
- GIN на tags.name (trigram) для автодополнения.
- GIN на media.hash (уникальность файлов).
- GIST/ltree на locations.path для быстрых выборок поддерева.

## Хранение файлов на NAS
- Базовый путь: `/data/gdemo/media/{workspace_id}/{user_id}/{item_id?}/`
- Эскизы: `/thumbs/` рядом с оригиналами.
- Документы/чеки: `/docs/`.

????? ????????:
- item_batches: id PK, workspace_id FK, location_id FK, title, created_by FK users, created_at.
- items.batch_id FK item_batches nullable � ??? ????????? ?????.
- ai_detection_reviews: id PK, detection_id FK, user_id FK, action (accept/reject/link/create/edit_location), payload JSONB, created_at.
??????????:
- ai_detection_objects: decision (pending/accepted/rejected), decided_by FK users nullable, decided_at timestamptz.
