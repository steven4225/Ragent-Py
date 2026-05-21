from fastapi import APIRouter

from ragent_python.config import get_settings
from ragent_python.infra.llm.resolver import resolve_generation_adapter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthcheck() -> dict[str, object]:
    settings = get_settings()
    generation_provider = resolve_generation_adapter().name
    return {
        "status": "ok",
        "service": "ragent-python",
        "environment": settings.environment,
        "generation_provider": generation_provider,
    }
