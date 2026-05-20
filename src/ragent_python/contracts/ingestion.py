from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ragent_python.contracts.public_api import utc_now_iso


class IngestionSourceModel(BaseModel):
    sourceType: Literal["upload", "object-storage", "external-url", "knowledge-import"]
    uri: str
    filename: str
    mimeType: str
    sizeBytes: int
    checksum: str | None = None


class IngestionParserConfigModel(BaseModel):
    parserType: str = "mock-parser"
    mode: Literal["mock", "adapter", "native"] = "mock"


class IngestionChunkingConfigModel(BaseModel):
    strategy: Literal["sentence", "paragraph", "markdown", "recursive", "semantic"] = "paragraph"
    targetSize: int = 1200
    overlap: int = 120


class IngestionEmbeddingConfigModel(BaseModel):
    enabled: bool = False
    model: str | None = None
    adapter: str | None = None


class IngestionIndexingConfigModel(BaseModel):
    enabled: bool = False
    indexName: str | None = None
    storeType: str | None = None


class IngestionExecutionPlanModel(BaseModel):
    parser: IngestionParserConfigModel = Field(default_factory=IngestionParserConfigModel)
    chunking: IngestionChunkingConfigModel = Field(default_factory=IngestionChunkingConfigModel)
    embedding: IngestionEmbeddingConfigModel = Field(default_factory=IngestionEmbeddingConfigModel)
    indexing: IngestionIndexingConfigModel = Field(default_factory=IngestionIndexingConfigModel)


class IngestionProcessingTraceEventModel(BaseModel):
    traceId: str
    taskId: str
    stage: Literal[
        "task-created",
        "accepted",
        "queued",
        "worker-claimed",
        "parsing",
        "chunking",
        "embedding",
        "indexing",
        "completed",
        "failed",
        "retry-scheduled",
    ]
    level: Literal["info", "warn", "error"]
    status: Literal["pending", "running", "succeeded", "failed"]
    message: str
    timestamp: str = Field(default_factory=utc_now_iso)
    tenantId: str | None = None
    orgId: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionTaskCreateRequestModel(BaseModel):
    traceId: str
    knowledgeBaseId: str
    documentId: str
    requestedBy: str
    tenantId: str | None = None
    orgId: str | None = None
    source: IngestionSourceModel
    executionPlan: IngestionExecutionPlanModel
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionTaskStatusModel(BaseModel):
    taskId: str
    traceId: str
    knowledgeBaseId: str
    documentId: str
    requestedBy: str
    tenantId: str | None = None
    orgId: str | None = None
    source: IngestionSourceModel
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"]
    currentStage: Literal["queued", "parser", "chunker", "embedding", "indexing", "completed", "failed"]
    attemptCount: int = 0
    maxAttempts: int = 3
    retryable: bool = False
    nextRunAt: str | None = None
    retryAfterSec: int = 0
    failureReason: str | None = None
    failureStage: str | None = None
    createdAt: str = Field(default_factory=utc_now_iso)
    updatedAt: str = Field(default_factory=utc_now_iso)
    startedAt: str | None = None
    finishedAt: str | None = None
    errorMessage: str | None = None
    executionPlan: IngestionExecutionPlanModel
    parserResult: dict[str, Any] | None = None
    embeddingResult: dict[str, Any] | None = None
    indexWriteResult: dict[str, Any] | None = None
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[IngestionProcessingTraceEventModel] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionTaskListResponseModel(BaseModel):
    items: list[IngestionTaskStatusModel] = Field(default_factory=list)
