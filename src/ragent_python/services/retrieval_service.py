from __future__ import annotations

from time import perf_counter

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalResponseModel, RetrievalTimingModel
from ragent_python.retrieval.providers import extract_terms, get_retrieval_provider


def execute_retrieval(request: InternalRetrievalRequestModel) -> RetrievalResponseModel:
    started = perf_counter()
    query_terms = extract_terms(request.query)
    retrieval_provider = get_retrieval_provider()
    chunks = retrieval_provider.search(request, query_terms)
    top_k = max(1, min(request.topK, 20))

    return RetrievalResponseModel(
        traceId=request.traceId,
        chunks=chunks[:top_k],
        timing=RetrievalTimingModel(totalMs=(perf_counter() - started) * 1000),
        source=retrieval_provider.provider_name,
    )
