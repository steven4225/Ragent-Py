"""Core layer: orchestration, stream protocol, trace, runtime loop, domain types.

This layer holds the contracts that describe *what* the platform is, independent
of any concrete infra adapter or business module. Anything in `core/` must
remain free of dependencies on `infra/` or `modules/`.
"""
