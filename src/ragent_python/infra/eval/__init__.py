"""Eval infra: suite / case / metric contracts plus the suite registry.

Step F migrates the four RAGAS-style metrics currently living in
`web/lib/eval/metrics/*` (faithfulness, answer-relevance, context-precision,
context-recall) to Python. Step A only fixes the contract so modules can
already declare their `evals()` from day one and have them landed in the
shared `EvalSuiteRegistry`.
"""

from ragent_python.infra.eval.contract import (
    EvalCase,
    EvalMetric,
    EvalMetricResult,
    EvalSuite,
    EvalSuiteResult,
)
from ragent_python.infra.eval.registry import (
    EvalSuiteRegistry,
    default_eval_suite_registry,
)

__all__ = [
    "EvalCase",
    "EvalMetric",
    "EvalMetricResult",
    "EvalSuite",
    "EvalSuiteRegistry",
    "EvalSuiteResult",
    "default_eval_suite_registry",
]
