from fastapi import FastAPI

from ragent_python.api.health import router as health_router
from ragent_python.api.internal_chat import router as internal_chat_router
from ragent_python.api.internal_ingestion import router as internal_ingestion_router
from ragent_python.api.internal_mcp import router as internal_mcp_router
from ragent_python.api.internal_retrieval import router as internal_retrieval_router
from ragent_python.config import get_settings
from ragent_python.modules import bootstrap_default_modules


def create_app() -> FastAPI:
    settings = get_settings()
    bootstrap_default_modules()
    app = FastAPI(
        title="Ragent Python Backend",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )
    app.include_router(health_router)
    app.include_router(internal_chat_router)
    app.include_router(internal_ingestion_router)
    app.include_router(internal_mcp_router)
    app.include_router(internal_retrieval_router)
    return app


app = create_app()
