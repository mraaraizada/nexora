from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router

app = FastAPI(
    title="NEXORA — Connected Publishing Infrastructure",
    description=(
        "One API. Multiple Platforms. Connected Publishing.\n\n"
        "Accepts a single message and distributes it across multiple supported "
        "third-party platforms through their official APIs: one request, "
        "independent per-platform publishing, a unified result."
    ),
    version="1.0.0",
)

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
    """Turns pydantic's default validation error shape into a flat, readable list of
    {field, message} pairs instead of its deeply-nested default format."""
    errors = [{"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": errors})


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "NEXORA", "docs": "/docs", "endpoint": "POST /posting"}
