from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalChunkModel
from ragent_python.config import get_settings
from ragent_python.modules.demo_corpus.provider import LocalStaticRetrievalProvider
from ragent_python.retrieval.bm25_provider import BM25RetrievalProvider
from ragent_python.retrieval.corpus import iter_ingestion_corpus, iter_local_corpus
from ragent_python.retrieval.reranker import BGEReranker, HeuristicReranker, NoopReranker


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

    def index_chunks(self, *args, **kwargs): ...


class IngestionTaskRetrievalProvider:
    provider_name = "python-ingestion-retrieval"

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]:
        results: list[RetrievalChunkModel] = []
        for chunk in iter_ingestion_corpus(request):
            score = score_text([chunk.title, chunk.content, *[str(value) for value in chunk.metadata.values() if isinstance(value, str)]], query_terms)
            if score <= 0:
                continue
            results.append(
                RetrievalChunkModel(
                    chunkId=chunk.chunk_id,
                    knowledgeBaseId=chunk.knowledge_base_id,
                    documentId=chunk.document_id,
                    title=chunk.title,
                    content=chunk.content,
                    score=float(score) + 0.25,
                    source=self.provider_name,
                    metadata=chunk.metadata,
                )
            )
        return results


class HybridRetrievalProvider:
    provider_name = "python-composite-retrieval"

    def __init__(
        self,
        *,
        dense_provider: SearchProvider | None,
        keyword_provider: SearchProvider,
        fallback_providers: list[SearchProvider],
        reranker,
        rerank_candidate_count: int,
        retrieval_weight: float,
        rerank_weight: float,
    ) -> None:
        self._dense_provider = dense_provider
        self._keyword_provider = keyword_provider
        self._fallback_providers = fallback_providers
        self._reranker = reranker
        self._rerank_candidate_count = max(1, rerank_candidate_count)
        self._retrieval_weight = retrieval_weight
        self._rerank_weight = rerank_weight

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]:
        dense_results = self._safe_search(self._dense_provider, request, query_terms) if self._dense_provider else []
        keyword_results = self._safe_search(self._keyword_provider, request, query_terms)
        fused_results = self._fuse_dense_and_keyword(dense_results, keyword_results)
        if fused_results:
            return self._apply_reranker_if_available(request.query, fused_results)

        fallback_results = [chunk for provider in self._fallback_providers for chunk in self._safe_search(provider, request, query_terms)]
        return sorted(fallback_results, key=lambda item: item.score, reverse=True)

    def _safe_search(
        self,
        provider: SearchProvider | None,
        request: InternalRetrievalRequestModel,
        query_terms: list[str],
    ) -> list[RetrievalChunkModel]:
        if provider is None:
            return []
        try:
            return provider.search(request, query_terms)
        except Exception:
            return []

    def _fuse_dense_and_keyword(
        self,
        dense_results: list[RetrievalChunkModel],
        keyword_results: list[RetrievalChunkModel],
    ) -> list[RetrievalChunkModel]:
        if not dense_results and not keyword_results:
            return []

        dense_ranks = {chunk.chunkId: index + 1 for index, chunk in enumerate(dense_results)}
        keyword_ranks = {chunk.chunkId: index + 1 for index, chunk in enumerate(keyword_results)}
        dense_map = {chunk.chunkId: chunk for chunk in dense_results}
        keyword_map = {chunk.chunkId: chunk for chunk in keyword_results}
        fused: list[RetrievalChunkModel] = []
        for chunk_id in {*dense_map.keys(), *keyword_map.keys()}:
            dense_chunk = dense_map.get(chunk_id)
            keyword_chunk = keyword_map.get(chunk_id)
            retrieval_mode = "hybrid" if dense_chunk and keyword_chunk else "vector" if dense_chunk else "keyword"
            base_chunk = dense_chunk or keyword_chunk
            assert base_chunk is not None
            dense_score = 1.0 / (60.0 + dense_ranks[chunk_id]) if chunk_id in dense_ranks else 0.0
            keyword_score = 1.0 / (60.0 + keyword_ranks[chunk_id]) if chunk_id in keyword_ranks else 0.0
            fused_score = dense_score + keyword_score
            fused.append(
                base_chunk.model_copy(
                    update={
                        "score": fused_score,
                        "metadata": {
                            **base_chunk.metadata,
                            "retrievalMode": retrieval_mode,
                            "fusionStrategy": "rrf" if retrieval_mode == "hybrid" else "single-source",
                            "denseSource": dense_chunk.source if dense_chunk else None,
                            "keywordSource": keyword_chunk.source if keyword_chunk else None,
                            "denseRank": dense_ranks.get(chunk_id),
                            "keywordRank": keyword_ranks.get(chunk_id),
                            "denseScore": round(dense_score, 6),
                            "keywordScore": round(keyword_score, 6),
                            "fusionScore": round(fused_score, 6),
                        },
                    }
                )
            )
        fused.sort(key=lambda item: item.score, reverse=True)
        return fused

    def _apply_reranker_if_available(self, query: str, fused_results: list[RetrievalChunkModel]) -> list[RetrievalChunkModel]:
        candidate_count = min(self._rerank_candidate_count, len(fused_results))
        candidates = fused_results[:candidate_count]
        remaining = fused_results[candidate_count:]
        try:
            reranked = self._reranker.rerank(query, candidates, 0)
        except Exception:
            return fused_results
        if not reranked:
            return fused_results

        retrieval_scores = {chunk.chunkId: chunk.score for chunk in candidates}
        retrieval_min, retrieval_max = _min_max(list(retrieval_scores.values()))
        rerank_scores = {chunk.chunkId: chunk.score for chunk in reranked}
        rerank_min, rerank_max = _min_max(list(rerank_scores.values()))

        blended: list[RetrievalChunkModel] = []
        for chunk in reranked:
            normalized_retrieval = _normalize(retrieval_scores.get(chunk.chunkId, 0.0), retrieval_min, retrieval_max)
            normalized_rerank = _normalize(rerank_scores.get(chunk.chunkId, 0.0), rerank_min, rerank_max)
            final_score = self._retrieval_weight * normalized_retrieval + self._rerank_weight * normalized_rerank
            blended.append(
                chunk.model_copy(
                    update={
                        "score": final_score,
                        "metadata": {
                            **chunk.metadata,
                            "retrievalScoreBeforeRerank": round(retrieval_scores.get(chunk.chunkId, 0.0), 6),
                            "rerankApplied": True,
                            "finalScore": round(final_score, 6),
                        },
                    }
                )
            )
        blended.sort(key=lambda item: item.score, reverse=True)
        return blended + remaining


def build_default_retrieval_provider() -> HybridRetrievalProvider:
    settings = get_settings()
    qdrant_provider = _build_qdrant_provider()
    keyword_provider = BM25RetrievalProvider()
    fallback_providers: list[SearchProvider] = [
        IngestionTaskRetrievalProvider(),
        LocalStaticRetrievalProvider(),
    ]
    dense_provider = qdrant_provider if settings.retrieval_backend in {"qdrant", "hybrid"} else None
    return HybridRetrievalProvider(
        dense_provider=dense_provider,
        keyword_provider=keyword_provider,
        fallback_providers=fallback_providers,
        reranker=_build_reranker(),
        rerank_candidate_count=settings.rerank_candidate_count,
        retrieval_weight=settings.rerank_retrieval_weight,
        rerank_weight=settings.rerank_model_weight,
    )


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
def _build_reranker():
    settings = get_settings()
    backend = settings.reranker_backend.strip().lower() or "auto"
    bge_url = settings.bge_reranker_url.strip() or settings.legacy_bge_reranker_url.strip()
    if backend == "none":
        return NoopReranker()
    if backend in {"bge", "auto"} and bge_url:
        return BGEReranker(endpoint=bge_url, timeout_ms=settings.reranker_timeout_ms)
    return HeuristicReranker()


@lru_cache(maxsize=1)
def get_retrieval_provider() -> HybridRetrievalProvider:
    return build_default_retrieval_provider()


def get_index_provider(store_type: str | None):
    normalized = (store_type or "").strip().lower()
    if normalized not in {"qdrant", "mock-qdrant"}:
        return None
    return _build_qdrant_provider()


def clear_retrieval_provider_cache() -> None:
    get_settings.cache_clear()
    _build_qdrant_provider.cache_clear()
    _build_reranker.cache_clear()
    get_retrieval_provider.cache_clear()


def _min_max(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    return min(values), max(values)


def _normalize(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 1.0 if value > 0 else 0.0
    return (value - minimum) / (maximum - minimum)
