from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="PYTHON_ENV")
    log_level: str = Field(default="info", alias="PYTHON_LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="PYTHON_HOST")
    port: int = Field(default=8000, alias="PYTHON_PORT")
    retrieval_backend: str = Field(default="hybrid", alias="PYTHON_RETRIEVAL_BACKEND")
    ingestion_backend: str = Field(default="sqlite", alias="PYTHON_INGESTION_BACKEND")
    ingestion_sqlite_path: str = Field(
        default=str(PROJECT_ROOT / ".runtime" / "ingestion.db"),
        alias="PYTHON_INGESTION_SQLITE_PATH",
    )
    ingestion_worker_poll_ms: int = Field(default=1000, alias="PYTHON_INGESTION_WORKER_POLL_MS")
    ingestion_worker_batch_size: int = Field(default=10, alias="PYTHON_INGESTION_WORKER_BATCH_SIZE")
    qdrant_url: str = Field(default="", alias="PYTHON_QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="PYTHON_QDRANT_API_KEY")
    qdrant_collection: str = Field(default="ragent_python_chunks", alias="PYTHON_QDRANT_COLLECTION")
    qdrant_timeout_ms: int = Field(default=5000, alias="PYTHON_QDRANT_TIMEOUT_MS")
    qdrant_vector_size: int = Field(default=8, alias="PYTHON_QDRANT_VECTOR_SIZE")
    reranker_backend: str = Field(default="auto", alias="PYTHON_RERANKER_BACKEND")
    reranker_timeout_ms: int = Field(default=10000, alias="PYTHON_RERANKER_TIMEOUT_MS")
    bge_reranker_url: str = Field(default="", alias="PYTHON_BGE_RERANKER_URL")
    legacy_bge_reranker_url: str = Field(default="", alias="BGE_RERANKER_URL")
    rerank_candidate_count: int = Field(default=20, alias="PYTHON_RERANK_CANDIDATE_COUNT")
    rerank_retrieval_weight: float = Field(default=0.3, alias="PYTHON_RERANK_RETRIEVAL_WEIGHT")
    rerank_model_weight: float = Field(default=0.7, alias="PYTHON_RERANK_MODEL_WEIGHT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
