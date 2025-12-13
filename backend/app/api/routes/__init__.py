from fastapi import APIRouter

from app.api.routes import health, auth, items, locations, ai, media, imports, logs


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(items.router)
api_router.include_router(locations.router)
api_router.include_router(ai.router)
api_router.include_router(media.router)
api_router.include_router(imports.router)
api_router.include_router(logs.router)
