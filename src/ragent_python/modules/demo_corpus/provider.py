"""Local-static retrieval provider for the demo corpus.

A trivial keyword-overlap scorer over the six demo-corpus chunks. Used by
`HybridRetrievalProvider` as one of its fallback providers and by tests as
a deterministic, no-network corpus. The class previously lived in
`retrieval/providers.py`; moving it here makes `modules/demo_corpus/` the
single owner of both the data and its query path.

`provider_name` and the score/metadata shape are preserved so existing
clients and snapshots are unchanged.
"""

from __future__ import annotations

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalChunkModel
from ragent_python.modules.demo_corpus.corpus import iter_local_corpus


def _extract_terms(query: str) -> list[str]:
    return [
        term.strip()
        for term in query.lower().split()
        if term.strip() and len(term.strip()) >= 2
    ]


def _score_text(haystack_parts: list[str], query_terms: list[str]) -> int:
    haystack = " ".join(haystack_parts).lower()
    return sum(1 for term in query_terms if term in haystack)


class LocalStaticRetrievalProvider:
    provider_name = "python-local-retrieval"

    def search(
        self,
        request: InternalRetrievalRequestModel,
        query_terms: list[str] | None = None,
    ) -> list[RetrievalChunkModel]:
        effective_terms = query_terms if query_terms is not None else _extract_terms(request.query)
        results: list[RetrievalChunkModel] = []
        for chunk in iter_local_corpus(request):
            score = _score_text([chunk.title, chunk.content, *chunk.terms], effective_terms)
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
                    metadata={**chunk.metadata, "provider": "local-static"},
                )
            )
        return results
