from __future__ import annotations

from time import perf_counter

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalResponseModel, RetrievalTimingModel
from ragent_python.retrieval.providers import build_default_retrieval_provider, extract_terms


retrieval_provider = build_default_retrieval_provider()


def execute_retrieval(request: InternalRetrievalRequestModel) -> RetrievalResponseModel:
    started = perf_counter()
    query_terms = extract_terms(request.query)
    chunks = retrieval_provider.search(request, query_terms)
    top_k = max(1, min(request.topK, 20))

    return RetrievalResponseModel(
        traceId=request.traceId,
        chunks=chunks[:top_k],
        timing=RetrievalTimingModel(totalMs=(perf_counter() - started) * 1000),
        source=retrieval_provider.provider_name,
    )
