from fastapi import APIRouter, Depends

from app.api.auth_deps import require_user
from .routes import auth, cities, events, gis, health, ingestion, merges, places, sources

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(cities.router, dependencies=[Depends(require_user)])
api_router.include_router(events.router, dependencies=[Depends(require_user)])
api_router.include_router(sources.router, dependencies=[Depends(require_user)])
api_router.include_router(ingestion.router, dependencies=[Depends(require_user)])
api_router.include_router(places.router, dependencies=[Depends(require_user)])
api_router.include_router(merges.router, dependencies=[Depends(require_user)])
api_router.include_router(gis.router, dependencies=[Depends(require_user)])
