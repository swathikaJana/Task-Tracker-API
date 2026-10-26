from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness check: confirms that the API process is responding."""
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(request: Request) -> JSONResponse:
    """Readiness check: verifies required storage and reports cache health."""
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "ok"
    except SQLAlchemyError:
        database_status = "unavailable"

    redis_status = "ok" if request.app.state.cache.ping() else "unavailable"
    overall_status = "ok" if database_status == "ok" else "unavailable"
    status_code = 200 if database_status == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "dependencies": {"database": database_status, "redis": redis_status},
        },
    )
