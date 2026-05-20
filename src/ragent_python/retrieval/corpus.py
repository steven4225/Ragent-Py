from __future__ import annotations

from dataclasses import dataclass

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.storage.ingestion_repository import ingestion_repository


@dataclass(frozen=True, slots=True)
class LocalKnowledgeChunk:
    chunk_id: str
    knowledge_base_id: str
    document_id: str
    title: str
    content: str
    terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalCorpusChunk:
    chunk_id: str
    knowledge_base_id: str
    document_id: str
    title: str
    content: str
    tenant_id: str | None
    org_id: str | None
    metadata: dict[str, object]
    source: str
    terms: tuple[str, ...] = ()


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


def iter_local_corpus(request: InternalRetrievalRequestModel) -> list[RetrievalCorpusChunk]:
    visible_corpus = (
        [chunk for chunk in LOCAL_KNOWLEDGE if chunk.knowledge_base_id in request.knowledgeBaseIds]
        if request.knowledgeBaseIds
        else list(LOCAL_KNOWLEDGE)
    )
    return [
        RetrievalCorpusChunk(
            chunk_id=chunk.chunk_id,
            knowledge_base_id=chunk.knowledge_base_id,
            document_id=chunk.document_id,
            title=chunk.title,
            content=chunk.content,
            tenant_id=None,
            org_id=None,
            metadata={"provider": "local-static"},
            source="python-local-retrieval",
            terms=chunk.terms,
        )
        for chunk in visible_corpus
    ]


def iter_ingestion_corpus(request: InternalRetrievalRequestModel) -> list[RetrievalCorpusChunk]:
    tasks = ingestion_repository.list(tenant_id=request.tenantId, org_id=request.orgId)
    results: list[RetrievalCorpusChunk] = []
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
            results.append(
                RetrievalCorpusChunk(
                    chunk_id=chunk_id,
                    knowledge_base_id=task.knowledgeBaseId,
                    document_id=document_id,
                    title=document_title,
                    content=text,
                    tenant_id=task.tenantId,
                    org_id=task.orgId,
                    metadata={
                        "provider": "ingestion-task",
                        "taskId": task.taskId,
                        "filename": task.source.filename,
                    },
                    source="python-ingestion-retrieval",
                )
            )
    return results
