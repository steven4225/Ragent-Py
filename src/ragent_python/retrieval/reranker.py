from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from ragent_python.contracts.public_api import RetrievalChunkModel
from ragent_python.retrieval.bm25_provider import tokenize


class Reranker(Protocol):
    provider_name: str

    def rerank(self, query: str, chunks: list[RetrievalChunkModel], top_k: int = 0) -> list[RetrievalChunkModel]: ...


class NoopReranker:
    provider_name = "noop-reranker"

    def rerank(self, query: str, chunks: list[RetrievalChunkModel], top_k: int = 0) -> list[RetrievalChunkModel]:
        return chunks[:top_k] if top_k > 0 else chunks


class HeuristicReranker:
    provider_name = "heuristic-reranker"

    def rerank(self, query: str, chunks: list[RetrievalChunkModel], top_k: int = 0) -> list[RetrievalChunkModel]:
        query_tokens = tokenize(query)
        reranked: list[RetrievalChunkModel] = []
        for chunk in chunks:
            title_tokens = tokenize(chunk.title)
            content_tokens = tokenize(chunk.content)
            title_overlap = sum(1 for token in query_tokens if token in title_tokens)
            content_overlap = sum(1 for token in query_tokens if token in content_tokens)
            rerank_score = float(content_overlap) + float(title_overlap) * 0.5
            reranked.append(
                chunk.model_copy(
                    update={
                        "score": rerank_score,
                        "metadata": {
                            **chunk.metadata,
                            "rerankSource": self.provider_name,
                            "rerankScore": rerank_score,
                        },
                    }
                )
            )
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k] if top_k > 0 else reranked


@dataclass(frozen=True, slots=True)
class BGEReranker:
    endpoint: str
    timeout_ms: int = 10000

    provider_name: str = "bge-reranker-v2-m3"

    def rerank(self, query: str, chunks: list[RetrievalChunkModel], top_k: int = 0) -> list[RetrievalChunkModel]:
        if not chunks:
            return []

        body = {
            "query": query,
            "documents": [f"{chunk.title} {chunk.content}".strip() for chunk in chunks],
        }
        with httpx.Client(timeout=self.timeout_ms / 1000) as client:
            response = client.post(self.endpoint, json=body, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        payload = response.json()

        scores = payload.get("scores", [])
        indices = payload.get("indices", [])
        reranked: list[RetrievalChunkModel] = []
        for position, raw_index in enumerate(indices):
            if not isinstance(raw_index, int) or raw_index < 0 or raw_index >= len(chunks):
                continue
            rerank_score = float(scores[position]) if position < len(scores) else float(len(chunks) - position)
            chunk = chunks[raw_index]
            reranked.append(
                chunk.model_copy(
                    update={
                        "score": rerank_score,
                        "metadata": {
                            **chunk.metadata,
                            "rerankSource": self.provider_name,
                            "rerankScore": rerank_score,
                        },
                    }
                )
            )
        return reranked[:top_k] if top_k > 0 else reranked
