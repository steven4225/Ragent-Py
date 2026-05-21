"""Renderer block registry.

Holds the pydantic block classes contributed by modules so downstream
consumers (the assistant-message serializer, the Step E TS type generator)
can discover all known block types. Dedup is by the literal value of the
class's ``type`` field — that field is what the frontend dispatches on.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def _extract_type_literal(block_cls: type[BaseModel]) -> str:
    field = block_cls.model_fields.get("type")
    if field is None:
        raise ValueError(
            f"Renderer block '{block_cls.__name__}' must declare a 'type' field."
        )
    default: Any = field.default
    if not isinstance(default, str) or not default:
        raise ValueError(
            f"Renderer block '{block_cls.__name__}' must default its 'type' field to "
            "a non-empty string literal."
        )
    return default


class RendererBlockRegistry:
    def __init__(self) -> None:
        self._blocks: dict[str, type[BaseModel]] = {}

    def register(self, block_cls: type[BaseModel]) -> None:
        type_literal = _extract_type_literal(block_cls)
        existing = self._blocks.get(type_literal)
        if existing is not None and existing is not block_cls:
            raise ValueError(
                f"Renderer block type '{type_literal}' already registered to "
                f"'{existing.__name__}', cannot re-register '{block_cls.__name__}'."
            )
        self._blocks[type_literal] = block_cls

    def get(self, type_literal: str) -> type[BaseModel] | None:
        return self._blocks.get(type_literal)

    def list_blocks(self) -> list[type[BaseModel]]:
        return list(self._blocks.values())

    def known_type_literals(self) -> list[str]:
        return list(self._blocks.keys())

    def clear(self) -> None:
        self._blocks.clear()


default_renderer_block_registry = RendererBlockRegistry()
