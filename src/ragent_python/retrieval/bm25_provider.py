from __future__ import annotations

import math
import re
from dataclasses import dataclass

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalChunkModel
from ragent_python.retrieval.corpus import iter_ingestion_corpus, iter_local_corpus


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
DEFAULT_K1 = 1.5
DEFAULT_B = 0.75
TITLE_BOOST = 0.3


@dataclass(frozen=True, slots=True)
class BM25Params:
    k1: float = DEFAULT_K1
    b: float = DEFAULT_B


class BM25RetrievalProvider:
    provider_name = "python-bm25-retrieval"

    def __init__(self, params: BM25Params | None = None) -> None:
        self._params = params or BM25Params()

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]:
        corpus = [*iter_ingestion_corpus(request), *iter_local_corpus(request)]
        if not corpus:
            return []

        query_tokens = tokenize(request.query)
        if not query_tokens:
            query_tokens = [term for term in query_terms if term]
        if not query_tokens:
            return []

        doc_tokens = [tokenize(chunk.content) for chunk in corpus]
        title_tokens = [tokenize(chunk.title) for chunk in corpus]
        avg_doc_len = average_doc_length(doc_tokens)
        avg_title_len = average_doc_length(title_tokens)
        doc_freq = build_doc_freq(doc_tokens)

        results: list[RetrievalChunkModel] = []
        for index, chunk in enumerate(corpus):
            body_score = bm25_score(query_tokens, doc_tokens[index], len(corpus), doc_freq, avg_doc_len, self._params)
            title_score = bm25_score(query_tokens, title_tokens[index], len(corpus), doc_freq, avg_title_len, self._params)
            total_score = body_score + TITLE_BOOST * title_score
            if total_score <= 0:
                continue
            results.append(
                RetrievalChunkModel(
                    chunkId=chunk.chunk_id,
                    knowledgeBaseId=chunk.knowledge_base_id,
                    documentId=chunk.document_id,
                    title=chunk.title,
                    content=chunk.content,
                    score=total_score,
                    source=self.provider_name,
                    metadata={
                        **chunk.metadata,
                        "provider": "bm25",
                        "retrievalMode": "keyword",
                        "bm25Score": round(total_score, 6),
                        "bm25BodyScore": round(body_score, 6),
                        "bm25TitleScore": round(title_score, 6),
                        "titleBoost": TITLE_BOOST,
                        "originSource": chunk.source,
                    },
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def term_frequency(tokens: list[str]) -> dict[str, int]:
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return freq


def average_doc_length(doc_tokens: list[list[str]]) -> float:
    if not doc_tokens:
        return 0.0
    return sum(len(tokens) for tokens in doc_tokens) / len(doc_tokens)


def build_doc_freq(doc_tokens: list[list[str]]) -> dict[str, int]:
    doc_freq: dict[str, int] = {}
    for tokens in doc_tokens:
        seen: set[str] = set()
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            doc_freq[token] = doc_freq.get(token, 0) + 1
    return doc_freq


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    total_docs: int,
    doc_freq: dict[str, int],
    avg_doc_len: float,
    params: BM25Params,
) -> float:
    if avg_doc_len <= 0 or total_docs <= 0 or not doc_tokens:
        return 0.0

    doc_len = float(len(doc_tokens))
    frequencies = term_frequency(doc_tokens)
    score = 0.0
    seen: set[str] = set()
    for token in query_tokens:
        if token in seen:
            continue
        seen.add(token)
        token_doc_freq = doc_freq.get(token, 0)
        if token_doc_freq <= 0:
            continue
        tf = float(frequencies.get(token, 0))
        if tf <= 0:
            continue
        idf = math.log((float(total_docs) - float(token_doc_freq) + 0.5) / (float(token_doc_freq) + 0.5) + 1.0)
        numerator = tf * (params.k1 + 1.0)
        denominator = tf + params.k1 * (1.0 - params.b + params.b * doc_len / avg_doc_len)
        score += idf * numerator / denominator
    return score
