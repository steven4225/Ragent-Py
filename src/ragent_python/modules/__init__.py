"""Business and platform-admin modules.

Each module lives in `modules/<name>/` with a `module.py` exposing a class
that satisfies `core.modules.Module`. Step B introduced the first real
module (`modules/platform_admin/`) which owns the three legacy MCP tools;
Step C adds `modules/demo_corpus/` which owns the six-chunk hand-curated
demo dataset and the matching `RetrievalSourceSpec`. Step D will add the
first business module (`modules/ecommerce/`).

`bootstrap_default_modules()` is the single registration entrypoint shared
by `mcp/registry.py` (lazy) and `main.create_app()` (eager). It is
idempotent and safe to call multiple times.
"""

from __future__ import annotations

from ragent_python.infra.registries.module_registry import (
    ModuleRegistry,
    default_module_registry,
)
from ragent_python.modules.demo_corpus.module import DemoCorpusModule
from ragent_python.modules.platform_admin.module import PlatformAdminModule


def bootstrap_default_modules(
    registry: ModuleRegistry | None = None,
) -> ModuleRegistry:
    """Register and bootstrap the built-in modules on the given registry.

    Defaults to the global `default_module_registry`. The call is idempotent:
    if a module is already registered we skip the `register()` step; the
    `bootstrap()` step is itself a no-op for already-bootstrapped modules.
    """

    target = registry or default_module_registry
    existing = {module.name for module in target.list_modules()}
    if PlatformAdminModule.name not in existing:
        target.register(PlatformAdminModule())
    if DemoCorpusModule.name not in existing:
        target.register(DemoCorpusModule())
    target.bootstrap()
    return target


__all__ = [
    "DemoCorpusModule",
    "PlatformAdminModule",
    "bootstrap_default_modules",
]
