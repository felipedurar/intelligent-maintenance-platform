from fastapi import APIRouter, Depends, Response, status

from platform_api.config import Settings, get_settings
from platform_api.database import check_database

router = APIRouter()


@router.get(
    "/health",
    summary="Liveness check",
    description="Returns basic application status without checking dependencies.",
)
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Checks whether required dependencies, currently PostgreSQL, are reachable.",
)
def readiness(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    database = check_database(settings)
    if not database.ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if database.ok else "degraded",
        "checks": {
            "database": {
                "ok": database.ok,
                "detail": database.detail,
            }
        },
    }
