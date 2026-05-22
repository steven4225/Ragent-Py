"""Demo-corpus data and corpus iterator.

The six chunks below previously lived in `retrieval/corpus.py` as
``LOCAL_KNOWLEDGE``. They are the platform's hand-curated demo dataset
(policy / ops / product samples) used by the local-static retrieval
provider and by BM25 as one of its corpora.

Moving them under `modules/demo_corpus/` is purely structural: contents,
ordering, term sets, and the `iter_local_corpus()` return shape are
unchanged. `retrieval/corpus.py` re-exports the public symbols so
existing call sites stay byte-for-byte compatible.
"""

from __future__ import annotations

from dataclasses import dataclass

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.retrieval.types import RetrievalCorpusChunk


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


DEMO_KNOWLEDGE_BASE_IDS: frozenset[str] = frozenset(
    {chunk.knowledge_base_id for chunk in LOCAL_KNOWLEDGE}
)


def iter_local_corpus(
    request: InternalRetrievalRequestModel,
) -> list[RetrievalCorpusChunk]:
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
