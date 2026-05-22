"""Demo-corpus module.

Owns the six-chunk hand-curated knowledge dataset that used to live inline
in `retrieval/corpus.py`. The module ships the data, the local-static
retrieval provider that scores keyword matches against it, and the
`RetrievalSourceSpec` that lets the rest of the platform discover the
source via `RetrievalSourceRegistry`.

Back-compat: `retrieval/corpus.py` and `retrieval/providers.py` re-export
the moved symbols so existing callers (`bm25_provider`, `providers`,
`services/retrieval_service`) need no changes.
"""

from ragent_python.modules.demo_corpus.corpus import (
    LOCAL_KNOWLEDGE,
    LocalKnowledgeChunk,
    iter_local_corpus,
)
from ragent_python.modules.demo_corpus.module import (
    DEMO_CORPUS_SOURCE_NAME,
    DemoCorpusModule,
    build_demo_corpus_retrieval_source_spec,
)
from ragent_python.modules.demo_corpus.provider import LocalStaticRetrievalProvider

__all__ = [
    "DEMO_CORPUS_SOURCE_NAME",
    "DemoCorpusModule",
    "LOCAL_KNOWLEDGE",
    "LocalKnowledgeChunk",
    "LocalStaticRetrievalProvider",
    "build_demo_corpus_retrieval_source_spec",
    "iter_local_corpus",
]
