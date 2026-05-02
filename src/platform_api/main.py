from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from platform_api.config import get_settings
from platform_api.openapi import API_DESCRIPTION, OPENAPI_TAGS
from platform_api.routes import chat, health, machines, models, monitoring, predictions, rag


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_tags=OPENAPI_TAGS,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 1,
            "defaultModelExpandDepth": 2,
            "displayRequestDuration": True,
            "filter": True,
            "persistAuthorization": True,
            "tryItOutEnabled": True,
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix, tags=["Health"])
    app.include_router(chat.router, prefix=f"{settings.api_prefix}/chat", tags=["Chat"])
    app.include_router(
        predictions.router,
        prefix=f"{settings.api_prefix}/predictions",
        tags=["Predictions"],
    )
    app.include_router(machines.router, prefix=f"{settings.api_prefix}/machines", tags=["Machines"])
    app.include_router(models.router, prefix=f"{settings.api_prefix}/models", tags=["Models"])
    app.include_router(rag.router, prefix=f"{settings.api_prefix}/rag", tags=["RAG"])
    app.include_router(
        monitoring.router,
        prefix=f"{settings.api_prefix}/monitoring",
        tags=["Monitoring"],
    )

    @app.get("/", include_in_schema=False)
    def root_docs_redirect() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.api_prefix}/docs")

    @app.get("/docs", include_in_schema=False)
    def docs_redirect() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.api_prefix}/docs")

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_redirect() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.api_prefix}/openapi.json")

    return app


app = create_app()
