"""Eval contracts.

The shape mirrors the TS-side runner in `web/lib/eval/eval-runner.ts` so the
migration in Step F is mechanical. A metric is a pure function over
``(query, answer, retrieved_chunks)`` returning a float in [0, 1] plus
optional diagnostic detail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class EvalCase:
    case_id: str
    query: str
    expected_chunk_ids: tuple[str, ...] = ()
    expected_answer: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class EvalMetricResult(BaseModel):
    metric: str
    score: float
    detail: dict[str, Any] = {}


@dataclass(frozen=True, slots=True)
class EvalMetric:
    name: str
    description: str
    compute: Callable[[str, str, list[str]], EvalMetricResult]


@dataclass(frozen=True, slots=True)
class EvalSuite:
    name: str
    module: str
    cases: tuple[EvalCase, ...]
    metrics: tuple[EvalMetric, ...]
    description: str = ""


class EvalSuiteResult(BaseModel):
    suite: str
    module: str
    case_results: list[dict[str, Any]] = []
    aggregate: dict[str, float] = {}
