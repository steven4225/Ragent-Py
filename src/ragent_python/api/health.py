from fastapi import APIRouter

from ragent_python.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthcheck() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "ragent-python",
        "environment": settings.environment,
    }
