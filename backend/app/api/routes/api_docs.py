"""The API's documentation (OpenAPI schema and Swagger UI), for signed-in users.

FastAPI serves them publicly by default (/api/docs, /redoc, /api/openapi.json);
they list every route and field, so they are served here behind sign-in instead.
"""

from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(tags=["documentation"], include_in_schema=False)


@router.get("/openapi.json")
def openapi_schema(request: Request) -> JSONResponse:
    return JSONResponse(request.app.openapi())


@router.get("/docs")
def swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="JSAN Road Event Intelligence API")
