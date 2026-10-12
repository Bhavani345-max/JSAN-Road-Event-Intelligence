from fastapi import APIRouter

from .routes import cities, events, gis, health, ingestion, merges, places, sources

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(cities.router)
api_router.include_router(events.router)
api_router.include_router(sources.router)
api_router.include_router(ingestion.router)
api_router.include_router(places.router)
api_router.include_router(merges.router)
api_router.include_router(gis.router)
