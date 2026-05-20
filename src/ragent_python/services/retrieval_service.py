from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalChunkModel, RetrievalResponseModel, RetrievalTimingModel


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


def extract_terms(query: str) -> list[str]:
    return [
        term.strip()
        for term in query.lower().split()
        if term.strip() and len(term.strip()) >= 2
    ]


def _score_chunk(chunk: LocalKnowledgeChunk, query_terms: list[str]) -> int:
    haystack = f"{chunk.title} {chunk.content} {' '.join(chunk.terms)}".lower()
    return sum(1 for term in query_terms if term in haystack)


def execute_retrieval(request: InternalRetrievalRequestModel) -> RetrievalResponseModel:
    started = perf_counter()
    query_terms = extract_terms(request.query)
    visible_corpus = (
        [chunk for chunk in LOCAL_KNOWLEDGE if chunk.knowledge_base_id in request.knowledgeBaseIds]
        if request.knowledgeBaseIds
        else list(LOCAL_KNOWLEDGE)
    )

    chunks = [
        RetrievalChunkModel(
            chunkId=chunk.chunk_id,
            knowledgeBaseId=chunk.knowledge_base_id,
            documentId=chunk.document_id,
            title=chunk.title,
            content=chunk.content,
            score=float(score),
            source="python-local-retrieval",
            metadata={},
        )
        for chunk in visible_corpus
        if (score := _score_chunk(chunk, query_terms)) > 0
    ]
    chunks.sort(key=lambda item: item.score, reverse=True)
    top_k = max(1, min(request.topK, 20))

    return RetrievalResponseModel(
        traceId=request.traceId,
        chunks=chunks[:top_k],
        timing=RetrievalTimingModel(totalMs=(perf_counter() - started) * 1000),
        source="python-local-retrieval",
    )
