"""`DemoCorpusModule` — first module to contribute a `RetrievalSourceSpec`.

It declares a single retrieval source named ``"demo_corpus"`` that builds
the `LocalStaticRetrievalProvider`. The selector activates the source
either when the request has no knowledge-base filter (default visibility)
or when at least one of the requested knowledge bases is one of the demo
corpus's bases (``kb_policy`` / ``kb_ops`` / ``kb_product``). The behaviour
matches what `iter_local_corpus()` already does internally, so swapping a
future caller from the legacy path to the registry-driven path is a
no-op.
"""

from __future__ import annotations

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.core.modules.contract import ModuleHookResult
from ragent_python.infra.registries.retrieval_source import RetrievalSourceSpec
from ragent_python.modules.demo_corpus.corpus import DEMO_KNOWLEDGE_BASE_IDS
from ragent_python.modules.demo_corpus.provider import LocalStaticRetrievalProvider


DEMO_CORPUS_SOURCE_NAME = "demo_corpus"


def _demo_corpus_selector(request: InternalRetrievalRequestModel) -> bool:
    if not request.knowledgeBaseIds:
        return True
    return any(kb_id in DEMO_KNOWLEDGE_BASE_IDS for kb_id in request.knowledgeBaseIds)


def build_demo_corpus_retrieval_source_spec() -> RetrievalSourceSpec:
    return RetrievalSourceSpec(
        name=DEMO_CORPUS_SOURCE_NAME,
        module="demo_corpus",
        build_provider=LocalStaticRetrievalProvider,
        selector=_demo_corpus_selector,
        fusion_weight=1.0,
        description=(
            "Six-chunk hand-curated policy/ops/product demo dataset. "
            "Used by the legacy HybridRetrievalProvider as a fallback and "
            "by BM25 as one of its corpora; exposed here so the platform "
            "registry can discover it as a module-owned source."
        ),
    )


class DemoCorpusModule:
    name = "demo_corpus"
    version = "0.1.0"

    def register(self) -> ModuleHookResult:
        return ModuleHookResult(
            retrieval_sources=(build_demo_corpus_retrieval_source_spec(),),
        )
