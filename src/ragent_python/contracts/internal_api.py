from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ragent_python.contracts.ingestion import IngestionTaskCreateRequestModel


class InternalChatRequestModel(BaseModel):
    message: str
    conversationId: str | None = None
    userId: str
    tenantId: str
    orgId: str | None = None
    role: Literal["user", "admin"] = "user"


class InternalRetrievalRequestModel(BaseModel):
    traceId: str
    query: str
    conversationId: str | None = None
    userId: str | None = None
    role: Literal["user", "admin"] | None = None
    orgId: str | None = None
    tenantId: str | None = None
    knowledgeBaseIds: list[str] = []
    topK: int = 6
    filters: dict[str, object] = {}


class InternalIngestionTaskCreateRequestModel(IngestionTaskCreateRequestModel):
    pass
