import json
import uuid

from dataclasses import MISSING, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from inspect import getmembers, isclass, isfunction, ismethod
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from sanic_routing.patterns import alpha, ext, nonemptystr, parse_date, slug

from sanic_ext.utils.typing import (
    UnionType,
    is_attrs,
    is_generic,
    is_msgspec,
    is_pydantic,
)


try:
    import attrs

    NOTHING: Any = attrs.NOTHING
except ImportError:
    NOTHING = object()

try:
    import msgspec

    from msgspec.inspect import Metadata as MsgspecMetadata
    from msgspec.inspect import type_info as msgspec_type_info

    MsgspecMetadata: Any = MsgspecMetadata
    NODEFAULT: Any = msgspec.NODEFAULT
    UNSET: Any = msgspec.UNSET

    class MsgspecAdapter(msgspec.Struct):
        name: str
        default: Any
        metadata: dict

except ImportError:

    def msgspec_type_info(struct):
        pass

    class MsgspecAdapter:
        pass

    MsgspecMetadata = object()
    NODEFAULT = object()
    UNSET = object()


class Definition:
    __nullable__: Optional[List[str]] = []
    __ignore__: Optional[List[str]] = []

    def __init__(self, **kwargs):
        self._fields: Dict[str, Any] = self.guard(kwargs)

    @property
    def fields(self):
        return self._fields

    def guard(self, fields):
        return {
            k: v
            for k, v in fields.items()
            if k in _properties(self).keys() or k.startswith("x-")
        }

    def serialize(self):
        return {
            k: self._value(v)
            for k, v in _serialize(self.fields).items()
            if (
                k not in self.__ignore__
                and (
                    v is not None
                    or (
                        isinstance(self.__nullable__, list)
                        and (not self.__nullable__ or k in self.__nullable__)
                    )
                )
            )
        }

    def __str__(self):
        return json.dumps(self.serialize())

    @staticmethod
    def _value(value):
        if isinstance(value, Enum):
            return value.value
        return value


class Schema(Definition):
    title: str
    description: str
    type: str
    format: str
    nullable: bool
    required: bool
    default: None
    example: None
    oneOf: List[Definition]
    anyOf: List[Definition]
    allOf: List[Definition]

    additionalProperties: Dict[str, str]
    multipleOf: int
    maximum: int
    exclusiveMaximum: bool
    minimum: int
    exclusiveMinimum: bool
    maxLength: int
    minLength: int
    pattern: str
    enum: Union[List[Any], Enum]

    @staticmethod
    def make(value, **kwargs):
        _type = type(value)
        origin = get_origin(value)
        args = get_args(value)
        if origin in (Union, UnionType):
            if type(None) in args:
                kwargs["nullable"] = True

            filtered = [arg for arg in args if arg is not type(None)]  # noqa

            if len(filtered) == 1:
                return Schema.make(filtered[0], **kwargs)
            return Schema(
                oneOf=[Schema.make(arg) for arg in filtered], **kwargs
            )

        for field in ("type", "format"):
            kwargs.pop(field, None)

        if isinstance(value, Schema):
            return value
        if value == bool:
            return Boolean(**kwargs)
        elif value == int:
            return Integer(**kwargs)
        elif value == float:
            return Float(**kwargs)
        elif value == str or value in (nonemptystr, ext, slug, alpha):
            return String(**kwargs)
        elif value == bytes:
            return Byte(**kwargs)
        elif value == bytearray:
            return Binary(**kwargs)
        elif value == date:
            return Date(**kwargs)
        elif value == time:
            return Time(**kwargs)
        elif value == datetime or value is parse_date:
            return DateTime(**kwargs)
        elif value == uuid.UUID:
            return UUID(**kwargs)
        elif value == Any:
            return AnyValue(**kwargs)

        if _type == bool:
            return Boolean(default=value, **kwargs)
        elif _type == int:
            return Integer(default=value, **kwargs)
        elif _type == float:
            return Float(default=value, **kwargs)
        elif _type == str:
            return String(default=value, **kwargs)
        elif _type == bytes:
            return Byte(default=value, **kwargs)
        elif _type == bytearray:
            return Binary(default=value, **kwargs)
        elif _type == date:
            return Date(**kwargs)
        elif _type == time:
            return Time(**kwargs)
        elif _type == datetime:
            return DateTime(**kwargs)
        elif _type == uuid.UUID:
            return UUID(**kwargs)
        elif _type == list:
            if len(value) == 0:
                schema = Schema(nullable=True)
            elif len(value) == 1:
                schema = Schema.make(value[0])
            else:
                schema = Schema(oneOf=[Schema.make(x) for x in value])

            return Array(schema, **kwargs)
        elif _type == dict:
            return Object.make(value, **kwargs)
        elif (
            (is_generic(value) or is_generic(_type))
            and origin == dict
            and len(args) == 2
        ):
            kwargs["additionalProperties"] = Schema.make(args[1])
            return Object(**kwargs)
        elif (is_generic(value) or is_generic(_type)) and origin == list:
            kwargs.pop("items", None)
            return Array(Schema.make(args[0]), **kwargs)
        elif _type is type(Enum):
            available = [item.value for item in value.__members__.values()]
            available_types = list({type(item) for item in available})
            schema_type = (
                available_types[0] if len(available_types) == 1 else "string"
            )
            return Schema.make(
                schema_type,
                enum=[item.value for item in value.__members__.values()],
            )
        else:
            return Object.make(value, **kwargs)


class Boolean(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="boolean", **kwargs)


class Integer(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="integer", format="int32", **kwargs)


class Long(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="integer", format="int64", **kwargs)


class Float(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="number", format="float", **kwargs)


class Double(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="number", format="double", **kwargs)


class String(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", **kwargs)


class Byte(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="byte", **kwargs)


class Binary(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="binary", **kwargs)


class Date(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="date", **kwargs)


class Time(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="time", **kwargs)


class DateTime(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="date-time", **kwargs)


class Password(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="password", **kwargs)


class Email(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="email", **kwargs)


class UUID(Schema):
    def __init__(self, **kwargs):
        super().__init__(type="string", format="uuid", **kwargs)


class AnyValue(Schema):
    @classmethod
    def make(cls, value: Any, **kwargs):
        return cls(
            AnyValue={},
            **kwargs,
        )


class Object(Schema):
    properties: Dict[str, Schema]
    maxProperties: int
    minProperties: int

    def __init__(
        self, properties: Optional[Dict[str, Schema]] = None, **kwargs
    ):
        if properties:
            kwargs["properties"] = properties
        super().__init__(type="object", **kwargs)

    @classmethod
    def make(cls, value: Any, **kwargs):
        extra: Dict[str, Any] = {}

        # Extract from field metadata if msgspec, pydantic, attrs, or dataclass
        if isclass(value):
            fields = ()
            if is_pydantic(value):
                try:
                    value = value.__pydantic_model__
                except AttributeError:
                    ...
                extra = value.schema()["properties"]
            elif is_attrs(value):
                fields = value.__attrs_attrs__
            elif is_dataclass(value):
                fields = value.__dataclass_fields__.values()
            elif is_msgspec(value):
                # adapt to msgspec metadata layout -- annotated type --
                # to match dataclass "metadata" attribute
                fields = [
                    MsgspecAdapter(
                        name=f.name,
                        default=(
                            MISSING
                            if f.default in (UNSET, NODEFAULT)
                            else f.default
                        ),
                        metadata=getattr(f.type, "extra", {}),
                    )
                    for f in msgspec_type_info(value).fields
                ]

            if fields:
                extra = {
                    field.name: {
                        "title": field.name.title(),
                        **(
                            {"default": field.default}
                            if field.default not in (MISSING, NOTHING)
                            else {}
                        ),
                        **dict(field.metadata).get("openapi", {}),
                    }
                    for field in fields
                }

        return cls(
            {
                k: Schema.make(v, **extra.get(k, {}))
                for k, v in _properties(value).items()
            },
            **kwargs,
        )


class Array(Schema):
    items: Any
    maxItems: int
    minItems: int
    uniqueItems: bool

    def __init__(self, items: Any, **kwargs):
        super().__init__(type="array", items=Schema.make(items), **kwargs)


def _serialize(value) -> Any:
    if isinstance(value, Definition):
        return value.serialize()

    if isinstance(value, type) and issubclass(value, Enum):
        return [item.value for item in value.__members__.values()]

    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_serialize(v) for v in value]

    return value


def _properties(value: object) -> Dict:
    try:
        fields = {
            x: val
            for x, v in getmembers(value, _is_property)
            if (val := _extract(v)) and x in value.__dict__
        }
    except AttributeError:
        fields = {}

    cls = value if callable(value) else value.__class__
    extra = value if isinstance(value, dict) else {}
    try:
        annotations = get_type_hints(cls)
    except NameError:
        if hasattr(value, "__annotations__"):
            annotations = value.__annotations__
        else:
            annotations = {}
    annotations.pop("return", None)
    try:
        output = {
            k: v
            for k, v in {**fields, **annotations, **extra}.items()
            if not k.startswith("_")
            and not (
                isclass(v)
                and isclass(cls)
                and v.__qualname__.endswith(
                    f"{getattr(cls, '__name__', '<unknown>')}."
                    f"{getattr(v, '__name__', '<unknown>')}"
                )
            )
        }
    except TypeError:
        return {}

    return output


def _extract(item):
    if isinstance(item, property):
        hints = get_type_hints(item.fget)
        return hints.get("return")
    return item


def _is_property(item):
    return not isfunction(item) and not ismethod(item)
