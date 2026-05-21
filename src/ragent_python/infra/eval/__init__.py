"""Eval infra: suite / case / metric contracts.

Step F migrates the four RAGAS-style metrics currently living in
`web/lib/eval/metrics/*` (faithfulness, answer-relevance, context-precision,
context-recall) to Python. Step A only fixes the contract so modules can
already declare their `evals()` from day one.
"""

from ragent_python.infra.eval.contract import (
    EvalCase,
    EvalMetric,
    EvalMetricResult,
    EvalSuite,
    EvalSuiteResult,
)

__all__ = [
    "EvalCase",
    "EvalMetric",
    "EvalMetricResult",
    "EvalSuite",
    "EvalSuiteResult",
]
