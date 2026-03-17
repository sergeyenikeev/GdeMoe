FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/root \
    ULTRALYTICS_CACHE_DIR=/root/.cache/ultralytics

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
# Прогреваем YOLO веса, чтобы избежать фолбэка "object"
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); print('YOLO weights cached')"

COPY ../app /app/app
COPY ../alembic.ini /app/alembic.ini
COPY ../alembic /app/alembic

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
