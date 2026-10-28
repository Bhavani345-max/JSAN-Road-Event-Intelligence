from fastapi import APIRouter, Depends

from app.api.auth_deps import require_admin, require_user
from .routes import api_docs, auth, cities, events, gis, health, ingestion, merges, places, sources, users

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
# User management: every route checks for an administrator itself (decision 0045).
api_router.include_router(users.router)
api_router.include_router(cities.router, dependencies=[Depends(require_user)])
api_router.include_router(events.router, dependencies=[Depends(require_user)])
api_router.include_router(sources.router, dependencies=[Depends(require_user)])
api_router.include_router(ingestion.router, dependencies=[Depends(require_admin)])
api_router.include_router(places.router, dependencies=[Depends(require_user)])
api_router.include_router(merges.router, dependencies=[Depends(require_user)])
api_router.include_router(gis.router, dependencies=[Depends(require_user)])
# The API's documentation, for signed-in users only.
api_router.include_router(api_docs.router, dependencies=[Depends(require_user)])
