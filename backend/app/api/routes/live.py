"""Live map layers from outside providers, passed through and never stored (decision 0054)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.services.tomtom_live import LiveFailed, LiveRefused, LiveUnavailable, TomTomLive

router = APIRouter(prefix="/live", tags=["live"])


def _tomtom(request: Request) -> TomTomLive:
    return request.app.state.tomtom_live


@router.get("/tomtom-incidents/status")
def tomtom_status(request: Request) -> dict:
    """Whether the TomTom live layer is available, and today's requests."""
    return _tomtom(request).status()


@router.get("/tomtom-incidents")
def tomtom_incidents(
    request: Request,
    response: Response,
    bbox: Annotated[str, Query(description="minLon,minLat,maxLon,maxLat (WGS 84), up to 10,000 km²")],
) -> dict:
    """TomTom's road incidents in the area on screen, as GeoJSON: asked for now, never stored."""
    try:
        answer = _tomtom(request).incidents(bbox)
    except LiveUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except LiveRefused as error:
        raise HTTPException(status_code=error.status, detail=str(error)) from None
    except LiveFailed as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    # TomTom's own cache-control (clause 11.4); the browser keeps it no longer than that.
    response.headers["Cache-Control"] = answer.cache_control
    return answer.collection
