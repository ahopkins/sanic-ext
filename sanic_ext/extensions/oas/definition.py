from __future__ import annotations

from abc import ABCMeta
from enum import Enum, auto
from types import SimpleNamespace
from typing import Any, Dict

from sanic.helpers import Default

from .base import BaseDecorator
from .registry import DefinitionRegistry

DEFAULT_META = {
    "duplicate": False,
    "merge": False,
}


class BaseEnum(str, Enum):
    def _generate_next_value_(name: str, *args) -> str:  # type: ignore
        return name.lower()

    def __str__(self):
        return self.name.lower()

    def serialize(self) -> str:
        return str(self)


class ParameterInChoice(BaseEnum):
    QUERY = auto()
    HEADER = auto()
    PATH = auto()
    COOKIE = auto()


class ParameterStyleChoice(BaseEnum):
    FORM = auto()
    SIMPLE = auto()
    MATRIX = auto()
    LABEL = auto()
    SPACE_DELIMITED = auto()
    PIPE_DELIMITED = auto()
    DEEP_OBJECT = auto()


class DefinitionType(ABCMeta):
    def __new__(cls, name, bases, attrs, **kwargs):
        meta = {**DEFAULT_META}
        if defined := attrs.pop("Meta", None):
            meta.update(
                {
                    k: v
                    for k, v in defined.__dict__.items()
                    if not k.startswith("_")
                }
            )
        attrs["meta"] = SimpleNamespace(**meta)
        gen_class = super().__new__(cls, name, bases, attrs, **kwargs)
        return gen_class


class Serializable:
    def serialize(self) -> Dict[str, Any]:
        return {
            self.serialize_key(key): self.serialize_value(value)
            for key, value in self.__dict__.items()
            if (not key.startswith("_") and not isinstance(value, Default))
        }

    @staticmethod
    def serialize_key(key: str) -> str:
        key = "".join(
            word.capitalize() if i else word
            for i, word in enumerate(key.rstrip("_").split("_"))
        )
        return key

    @staticmethod
    def serialize_value(value: Any) -> Any:
        if hasattr(value, "serialize"):
            return value.serialize()
        elif isinstance(value, list):
            return [Serializable.serialize_value(i) for i in value]
        elif isinstance(value, dict):
            return {
                key: Serializable.serialize_value(value)
                for key, value in value.items()
            }
        else:
            return value


class Definition(BaseDecorator, Serializable, metaclass=DefinitionType):
    def setup(self):
        key = f"{self._func.__module__}.{self._func.__qualname__}"
        DefinitionRegistry()[key] = self


class Extendable(Serializable):
    """
    This object is extendable according to Specification Extensions. For more
    information: https://swagger.io/specification/#specification-extensions

    As an example:

        @oas.foo(..., something_additional=1234)

    Will translate into the property:

        x-something-additional
    """

    _extension: Dict[str, Any]

    def __new__(cls, *args, **kwargs):
        if args and args[0] is cls:
            args = args[1:]
        if not hasattr(cls, "_init"):
            cls._init = cls.__init__
            cls.__init__ = lambda *a, **k: None

        obj = object.__new__(cls)
        obj._extension = {
            key: kwargs.pop(key)
            for key in list(kwargs.keys())
            if key not in cls.__dataclass_fields__
        }
        cls._init(obj, *args, **kwargs)

        return obj

    def serialize(self) -> Dict[str, Any]:
        base = super().serialize()
        base.update(self._extension)
        return base
