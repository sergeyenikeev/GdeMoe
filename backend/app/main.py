from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings
from app.db import base  # noqa: F401

app = FastAPI(title=settings.project_name)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root() -> dict:
    return {"message": "ГдеМоё — приложение, которое помнит за вас."}
