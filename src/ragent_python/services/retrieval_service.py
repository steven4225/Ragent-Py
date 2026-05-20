from __future__ import annotations

from time import perf_counter

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalResponseModel, RetrievalTimingModel, TraceStageModel, utc_now_iso
from ragent_python.retrieval.providers import extract_terms, get_retrieval_provider


def execute_retrieval(request: InternalRetrievalRequestModel) -> RetrievalResponseModel:
    started_at = utc_now_iso()
    started = perf_counter()
    query_terms = extract_terms(request.query)
    retrieval_provider = get_retrieval_provider()
    chunks = retrieval_provider.search(request, query_terms)
    top_k = max(1, min(request.topK, 20))
    total_ms = (perf_counter() - started) * 1000
    finished_at = utc_now_iso()
    top_chunks = chunks[:top_k]
    top_chunk = top_chunks[0] if top_chunks else None

    return RetrievalResponseModel(
        traceId=request.traceId,
        chunks=top_chunks,
        timing=RetrievalTimingModel(totalMs=total_ms),
        source=retrieval_provider.provider_name,
        traceStages=[
            TraceStageModel(
                stage="retrieval.plan",
                status="succeeded",
                metadata={
                    "query": request.query,
                    "topK": top_k,
                    "provider": retrieval_provider.provider_name,
                    "knowledgeBaseIds": request.knowledgeBaseIds,
                },
                startedAt=started_at,
                finishedAt=started_at,
                durationMs=0,
            ),
            TraceStageModel(
                stage="retrieval.execute",
                status="succeeded",
                metadata={
                    "provider": retrieval_provider.provider_name,
                    "chunkCount": len(top_chunks),
                    "topChunkId": top_chunk.chunkId if top_chunk is not None else None,
                    "topChunkSource": top_chunk.source if top_chunk is not None else None,
                    "retrievalMode": top_chunk.metadata.get("retrievalMode") if top_chunk is not None else None,
                    "fusionStrategy": top_chunk.metadata.get("fusionStrategy") if top_chunk is not None else None,
                },
                startedAt=started_at,
                finishedAt=finished_at,
                durationMs=max(0, round(total_ms)),
            ),
        ],
    )
