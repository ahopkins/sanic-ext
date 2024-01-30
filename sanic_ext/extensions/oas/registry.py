from __future__ import annotations

from typing import TYPE_CHECKING, List, Type, TypeVar

if TYPE_CHECKING:
    from .decorators import Definition  # type: ignore
else:
    Definition = TypeVar("Operation")


class DefinitionRegistry(dict[str, List[Definition]]):
    _registry: DefinitionRegistry

    def __setitem__(self, key: str, definition: Definition) -> None:
        self.setdefault(key, list())
        existing = next(
            (val for val in self[key] if isinstance(val, type(definition))),
            None,
        )
        if existing:
            if definition.meta.merge:
                existing.merge(definition)
                return
            if not definition.meta.duplicate:
                raise RuntimeError(
                    f"Cannot define multiple {definition.__class__.__name__} "
                    f"on {key}"
                )
        self[key].append(definition)

    def __new__(
        cls: Type[DefinitionRegistry], *args, **kwargs
    ) -> DefinitionRegistry:
        if existing := getattr(cls, "_registry", None):
            return existing
        cls._registry = super().__new__(cls)  # type: ignore
        return cls._registry
