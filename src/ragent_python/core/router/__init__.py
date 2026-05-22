"""Intent routing primitives (keyword-based today, embedding-based later).

We deliberately keep this package's `__init__` empty of cross-package
imports. `intent_router.py` depends on `infra.registries.intent_pattern`,
which in turn imports `core.router.intent` — auto-importing both
modules here would create a circular import. Consumers should import
the symbols they need from the leaf modules:

    from ragent_python.core.router.intent import IntentPattern
    from ragent_python.core.router.intent_router import (
        IntentRouter,
        RoutingDecision,
        default_intent_router,
    )
"""
