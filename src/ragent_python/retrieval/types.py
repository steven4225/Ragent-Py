"""Shared retrieval data types.

`RetrievalCorpusChunk` is the in-memory representation of a corpus chunk
used by every corpus iterator (the demo corpus, the ingestion corpus, and
any future module-owned corpus). It lives here — not under
`retrieval/corpus.py` — so that module code can import it without taking
a dependency back on the legacy `retrieval/corpus.py` re-export module.
"""

from __future__ import annotations

from dataclasses import dataclass


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
