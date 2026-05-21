"""Eval suite registry.

Modules contribute one or more `EvalSuite` instances via
`ModuleHookResult.evals`. The registry is the discovery point for the
(future) eval runner that lands in Step F.
"""

from __future__ import annotations

from ragent_python.infra.eval.contract import EvalSuite


class EvalSuiteRegistry:
    def __init__(self) -> None:
        self._suites: dict[str, EvalSuite] = {}

    def register(self, suite: EvalSuite) -> None:
        if suite.name in self._suites:
            raise ValueError(f"Eval suite '{suite.name}' already registered.")
        self._suites[suite.name] = suite

    def get(self, name: str) -> EvalSuite | None:
        return self._suites.get(name)

    def list_suites(self) -> list[EvalSuite]:
        return list(self._suites.values())

    def list_for_module(self, module: str) -> list[EvalSuite]:
        return [suite for suite in self._suites.values() if suite.module == module]

    def clear(self) -> None:
        self._suites.clear()


default_eval_suite_registry = EvalSuiteRegistry()
