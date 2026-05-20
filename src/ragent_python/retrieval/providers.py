from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalChunkModel
from ragent_python.config import get_settings
from ragent_python.storage.ingestion_repository import ingestion_repository


def extract_terms(query: str) -> list[str]:
    return [
        term.strip()
        for term in query.lower().split()
        if term.strip() and len(term.strip()) >= 2
    ]


def score_text(haystack_parts: list[str], query_terms: list[str]) -> int:
    haystack = " ".join(haystack_parts).lower()
    return sum(1 for term in query_terms if term in haystack)


class SearchProvider(Protocol):
    provider_name: str

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]: ...


class IndexProvider(Protocol):
    provider_name: str


@dataclass(frozen=True, slots=True)
class LocalKnowledgeChunk:
    chunk_id: str
    knowledge_base_id: str
    document_id: str
    title: str
    content: str
    terms: tuple[str, ...]


LOCAL_KNOWLEDGE: tuple[LocalKnowledgeChunk, ...] = (
    LocalKnowledgeChunk(
        chunk_id="chunk_policy_leave",
        knowledge_base_id="kb_policy",
        document_id="doc_policy_leave",
        title="Leave Policy Overview",
        content="Annual leave requests require manager approval and should be submitted three business days in advance.",
        terms=("leave", "vacation", "policy", "annual leave", "manager approval"),
    ),
    LocalKnowledgeChunk(
        chunk_id="chunk_policy_payroll",
        knowledge_base_id="kb_policy",
        document_id="doc_policy_payroll",
        title="Payroll and Benefits",
        content="Payroll closes on the 25th of each month. Benefit enrollment changes take effect on the first day of the next month.",
        terms=("payroll", "benefits", "salary", "policy", "enrollment"),
    ),
    LocalKnowledgeChunk(
        chunk_id="chunk_ops_incident",
        knowledge_base_id="kb_ops",
        document_id="doc_ops_incident",
        title="Incident Response Runbook",
        content="Priority 1 incidents require an incident commander, status updates every 15 minutes, and a follow-up review within 24 hours.",
        terms=("incident", "p1", "support", "runbook", "sla"),
    ),
    LocalKnowledgeChunk(
        chunk_id="chunk_ops_ticket",
        knowledge_base_id="kb_ops",
        document_id="doc_ops_ticket",
        title="Ticket Triage SOP",
        content="Support tickets should be routed by product area, urgency, and customer tier before escalation.",
        terms=("ticket", "support", "triage", "escalation", "ops"),
    ),
    LocalKnowledgeChunk(
        chunk_id="chunk_product_release",
        knowledge_base_id="kb_product",
        document_id="doc_product_release",
        title="Release Readiness Checklist",
        content="Release readiness requires QA signoff, rollout notes, rollback guidance, and stakeholder communication.",
        terms=("release", "product", "feature", "roadmap", "rollout"),
    ),
    LocalKnowledgeChunk(
        chunk_id="chunk_product_roadmap",
        knowledge_base_id="kb_product",
        document_id="doc_product_roadmap",
        title="Product Planning Notes",
        content="Roadmap reviews prioritize customer demand, implementation cost, and dependencies across teams.",
        terms=("roadmap", "product", "feature", "planning", "dependencies"),
    ),
)


class LocalStaticRetrievalProvider:
    provider_name = "python-local-retrieval"

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]:
        visible_corpus = (
            [chunk for chunk in LOCAL_KNOWLEDGE if chunk.knowledge_base_id in request.knowledgeBaseIds]
            if request.knowledgeBaseIds
            else list(LOCAL_KNOWLEDGE)
        )
        results: list[RetrievalChunkModel] = []
        for chunk in visible_corpus:
            score = score_text([chunk.title, chunk.content, *chunk.terms], query_terms)
            if score <= 0:
                continue
            results.append(
                RetrievalChunkModel(
                    chunkId=chunk.chunk_id,
                    knowledgeBaseId=chunk.knowledge_base_id,
                    documentId=chunk.document_id,
                    title=chunk.title,
                    content=chunk.content,
                    score=float(score),
                    source=self.provider_name,
                    metadata={"provider": "local-static"},
                )
            )
        return results


class IngestionTaskRetrievalProvider:
    provider_name = "python-ingestion-retrieval"

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]:
        tasks = ingestion_repository.list(tenant_id=request.tenantId, org_id=request.orgId)
        results: list[RetrievalChunkModel] = []
        for task in tasks:
            if task.status != "succeeded" or task.currentStage != "completed":
                continue
            if request.knowledgeBaseIds and task.knowledgeBaseId not in request.knowledgeBaseIds:
                continue

            parsed_document = None
            if isinstance(task.parserResult, dict):
                parsed_document = task.parserResult.get("parsedDocument")
            document_title = (
                parsed_document.get("title")
                if isinstance(parsed_document, dict) and isinstance(parsed_document.get("title"), str)
                else task.source.filename
            )

            for chunk in task.chunks:
                text = chunk.get("text") if isinstance(chunk, dict) else None
                chunk_id = chunk.get("chunkId") if isinstance(chunk, dict) else None
                document_id = chunk.get("documentId") if isinstance(chunk, dict) else None
                if not isinstance(text, str) or not isinstance(chunk_id, str) or not isinstance(document_id, str):
                    continue
                score = score_text([document_title, text, task.source.filename, task.knowledgeBaseId], query_terms)
                if score <= 0:
                    continue
                results.append(
                    RetrievalChunkModel(
                        chunkId=chunk_id,
                        knowledgeBaseId=task.knowledgeBaseId,
                        documentId=document_id,
                        title=document_title,
                        content=text,
                        score=float(score) + 0.25,
                        source=self.provider_name,
                        metadata={
                            "provider": "ingestion-task",
                            "taskId": task.taskId,
                            "filename": task.source.filename,
                        },
                    )
                )
        return results


class CompositeRetrievalProvider:
    provider_name = "python-composite-retrieval"

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers
        self._provider_priority = {
            provider.provider_name: index for index, provider in enumerate(providers)
        }

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]:
        aggregated: dict[str, RetrievalChunkModel] = {}
        for provider in self._providers:
            try:
                chunks = provider.search(request, query_terms)
            except Exception:
                continue
            for chunk in chunks:
                existing = aggregated.get(chunk.chunkId)
                if existing is None:
                    aggregated[chunk.chunkId] = chunk
                    continue
                if existing.source == chunk.source:
                    if chunk.score > existing.score:
                        aggregated[chunk.chunkId] = chunk
                    continue
                if existing.source != "python-qdrant-retrieval" and chunk.source == "python-qdrant-retrieval":
                    aggregated[chunk.chunkId] = chunk
                    continue
                if chunk.score > existing.score and existing.source != "python-qdrant-retrieval":
                    aggregated[chunk.chunkId] = chunk
        return sorted(
            aggregated.values(),
            key=lambda item: (
                self._provider_priority.get(item.source, len(self._provider_priority)),
                -item.score,
            ),
        )


def build_default_retrieval_provider() -> CompositeRetrievalProvider:
    settings = get_settings()
    providers: list[SearchProvider] = []
    qdrant_provider = _build_qdrant_provider()
    if settings.retrieval_backend in {"qdrant", "hybrid"} and qdrant_provider is not None:
        providers.append(qdrant_provider)
    if settings.retrieval_backend in {"local", "hybrid", "qdrant"}:
        providers.extend(
            [
                IngestionTaskRetrievalProvider(),
                LocalStaticRetrievalProvider(),
            ]
        )
    return CompositeRetrievalProvider(providers=providers)


@lru_cache(maxsize=1)
def _build_qdrant_provider():
    settings = get_settings()
    if not settings.qdrant_url.strip():
        return None
    from ragent_python.retrieval.qdrant_provider import QdrantIndexProvider

    return QdrantIndexProvider(
        base_url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection,
        timeout_ms=settings.qdrant_timeout_ms,
        vector_size=settings.qdrant_vector_size,
    )


@lru_cache(maxsize=1)
def get_retrieval_provider() -> CompositeRetrievalProvider:
    return build_default_retrieval_provider()


def get_index_provider(store_type: str | None):
    normalized = (store_type or "").strip().lower()
    if normalized not in {"qdrant", "mock-qdrant"}:
        return None
    return _build_qdrant_provider()


def clear_retrieval_provider_cache() -> None:
    get_settings.cache_clear()
    _build_qdrant_provider.cache_clear()
    get_retrieval_provider.cache_clear()
