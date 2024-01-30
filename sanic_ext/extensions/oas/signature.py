from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Type, TypedDict, Union
from uuid import UUID

from sanic.helpers import Default, _default

from .definition import (
    Extendable,
    ParameterInChoice,
    ParameterStyleChoice,
    Serializable,
)

try:
    from typing import NotRequired  # type: ignore
except ImportError:
    from typing_extensions import NotRequired


@dataclass
class Description(Serializable):
    description: Union[str, Default] = _default


@dataclass
class URL(Serializable):
    url: str


@dataclass
class ExternalDocument(Description, URL, Extendable):
    """Some documentation about external documents"""


@dataclass
class Name(Serializable):
    name: str


@dataclass
class Text(Serializable):
    text: str


@dataclass
class Summary(Serializable):
    summary: Union[str, Default] = _default


@dataclass
class Required(Serializable):
    required: Union[bool, Default] = _default


@dataclass
class Deprecated(Serializable):
    deprecated: bool = True


@dataclass
class ParameterIn(Serializable):
    in_: ParameterInChoice = ParameterInChoice.QUERY


@dataclass
class Schema(
    Serializable
):  # TODO: Schema https://swagger.io/specification/#schema-object
    model: Type[object] = str
    format: Union[
        Literal["date-time"],
        Literal["date"],
        Literal["time"],
        Literal["duration"],
        Literal["email"],
        Literal["idn-email"],
        Literal["hostname"],
        Literal["idn-hostname"],
        Literal["ipv4"],
        Literal["ipv6"],
        Literal["uuid"],
        Literal["uri"],
        Literal["uri-reference"],
        Literal["iri"],
        Literal["iri-reference"],
        Literal["uri-template"],
        Literal["json-pointer"],
        Literal["relative-json-pointer"],
        Literal["regex"],
        Default,
    ] = _default

    def __post_init__(self):
        if isinstance(self.model, Default):
            self.model = str
        elif self.model is UUID:
            self.model = str
            self.format = "uuid"
        elif self.model is datetime:
            self.model = str
            self.format = "date-time"
        elif self.model is date:
            self.model = str
            self.format = "date"
        elif self.model is timedelta:
            self.model = str
            self.format = "duration"

        self._format_validation()

    def _format_validation(self):
        # TODO: https://swagger.io/specification/#data-types
        if isinstance(self.model, Default) or isinstance(self.format, Default):
            return

        if (
            (
                self.model is int
                and self.format
                in (
                    "int32",
                    "int64",
                )
            )
            or (
                self.model is float
                and self.format
                in (
                    "float",
                    "double",
                )
            )
            or (
                self.model is str
                and self.format
                in (
                    "date-time",
                    "date",
                    "time",
                    "duration",
                    "email",
                    "idn-email",
                    "hostname",
                    "idn-hostname",
                    "ipv4",
                    "ipv6",
                    "uuid",
                    "uri",
                    "uri-reference",
                    "iri",
                    "iri-reference",
                    "uri-template",
                    "json-pointer",
                    "relative-json-pointer",
                    "regex",
                )
            )
        ):
            return

        raise ValueError(f"Invalid format for {self.model}: {self.format}")

    def serialize(self) -> Dict[str, Any]:
        base = super().serialize()
        model = base.pop("model")

        # TODO: https://swagger.io/specification/#data-types
        if model is str:
            base["type"] = "string"
        elif model is int:
            base["type"] = "integer"
            base.setdefault("format", "int32")
        elif model is float:
            base["type"] = "number"
            base["format"] = "float"
        elif model is bool:
            base["type"] = "boolean"
        elif model is list:
            base["type"] = "array"
        elif model is dict:
            base["type"] = "object"
        else:
            # TODO: Create a component for this model
            # https://swagger.io/specification/#reference-object
            # base["$ref"] = f"#/components/schemas/{self.model.__name__}"
            ...

        return base


@dataclass
class SchemaArg(Serializable):
    schema: Optional[
        Union[Default, Schema, str, float, int, bool, Reference]
    ] = _default

    def __post_init__(self):
        if isinstance(self.schema, dict):
            self.schema = Schema(**self.schema)


@dataclass
class SimpleExample(Serializable):
    example: Union[Any, Default] = _default


@dataclass
class Example(Description, Summary, Extendable):
    value: Any = None
    external_value: Union[Default, str] = _default

    def __post_init__(self):
        if not isinstance(self.external_value, Default) and self.value:
            raise ValueError
        super().__post_init__()


@dataclass
class Examples(Serializable):
    examples: Union[
        List[Dict[str, Union[Example, Reference]]], Default
    ] = _default


@dataclass
class Content(Serializable):
    content: Optional[
        Union[Default, Dict[str, Union[MediaType, MediaTypeDict]]]
    ] = _default

    def __post_init__(self):
        if isinstance(self.content, dict):
            self.content = {
                key: MediaType(**value) for key, value in self.content.items()
            }


@dataclass
class Parameter(
    Examples,
    SimpleExample,
    Deprecated,
    Required,
    Description,
    Content,
    SchemaArg,
    ParameterIn,
    Name,
    Extendable,
):
    style: Union[ParameterStyleChoice, Default] = _default
    allow_empty_value: Union[Default, bool] = _default
    allow_reserved: Union[Default, bool] = _default
    explode: Union[Default, bool] = _default

    __ENUMS__ = (("in_", ParameterInChoice), ("style", ParameterStyleChoice))

    def __post_init__(self):
        for name, choices in self.__ENUMS__:
            value = getattr(self, name)
            if not isinstance(value, choices) and not isinstance(
                value, Default
            ):
                setattr(self, name, choices(value))
            super().__post_init__()

        if self.in_ is ParameterInChoice.PATH:
            self.required = True

        # if self.style is ParameterStyleChoice.DEFAULT:
        #     self.style = (
        #         ParameterStyleChoice.FORM
        #         if self.in_
        #         in (ParameterInChoice.QUERY, ParameterInChoice.COOKIE)
        #         else ParameterStyleChoice.SIMPLE
        #     )

        if self.allow_empty_value and self.in_ is not ParameterInChoice.QUERY:
            raise ValueError

        # if isinstance(self.explode, Default):
        #     self.explode = self.style is ParameterStyleChoice.FORM

        if self.example and self.examples:
            raise ValueError("Cannot have both example and examples")
        # elif self.example:
        #     self.examples = [Example(value=self.example)]
        #     self.example = _default

        if isinstance(self.schema, Default) and isinstance(
            self.content, Default
        ):
            self.schema = str
        #     self.content = None
        # elif isinstance(self.schema, Default) and not isinstance(
        #     self.content, Default
        # ):
        #     self.schema = None
        # elif not isinstance(self.schema, Default) and isinstance(
        #     self.content, Default
        # ):
        #     self.content = None
        # else:
        elif not isinstance(self.schema, Default) and not isinstance(
            self.content, Default
        ):
            raise ValueError("Cannot have both schema and content")

        if self.schema and not isinstance(self.schema, Schema):
            self.schema = Schema(model=self.schema)


@dataclass
class Reference(Serializable):
    ...


@dataclass
class Header(
    Examples,
    SimpleExample,
    Deprecated,
    Required,
    Description,
    Content,
    SchemaArg,
    Extendable,
):
    allow_empty_value: Union[Default, bool] = _default
    allow_reserved: Union[Default, bool] = _default
    explode: Union[Default, bool] = _default


@dataclass
class Encoding(Serializable):
    content_type: Union[str, Default] = _default
    headers: Union[Dict[str, Union[Header, Reference]], Default] = _default
    style: Union[str, Default] = _default
    explode: Union[bool, Default] = _default
    allow_reserved: Union[bool, Default] = _default


@dataclass
class MediaType(Examples, SimpleExample, SchemaArg, Encoding, Extendable):
    def __post_init__(self):
        if isinstance(self.schema, Default):
            raise ValueError("MediaType must have a schema")
        if not isinstance(self.schema, Schema):
            self.schema = Schema(model=self.schema)
        super().__post_init__()


@dataclass
class Link(Description):
    ...
    # TODO: https://swagger.io/specification/#link-object


@dataclass
class RequestBody(Required, Description, Content):
    def __post_init__(self):
        if isinstance(self.content, Default):
            raise ValueError


@dataclass
class Headers(Serializable):
    headers: Union[Dict[str, Union[Header, Reference]], Default] = _default


@dataclass
class Links(Serializable):
    links: Union[Dict[str, Union[Link, Reference]], Default] = _default


@dataclass
class Status(Serializable):
    status_code: Union[int, Default] = _default

    def serialize(self) -> Dict[str, Any]:
        base = super().serialize()
        base.pop("statusCode", None)
        return base

    @property
    def status(self) -> str:
        if isinstance(self.status_code, Default):
            return "default"
        return str(self.status_code)


# TODO:
# - headers
# - links
@dataclass
class Response(Description, Headers, Content, Links, Status):
    def __post_init__(self):
        if isinstance(self.content, Default):
            raise ValueError("Response must have content")
        if not self.description or isinstance(self.description, Default):
            self.description = ""
        super().__post_init__()


@dataclass
class ResponseReference(Reference, Status):
    ...


@dataclass
class Callback(Serializable):
    ...


@dataclass
class SecurityScheme(Extendable):
    scheme: Union[Dict[str, List[str]], Default] = _default
    schemes: Union[List[Dict[str, List[str]]], Default] = _default

    def __post_init__(self):
        if isinstance(self.schemes, Default) and isinstance(
            self.scheme, Default
        ):
            raise ValueError("SecurityScheme must have a scheme")
        if not isinstance(self.schemes, Default) and not isinstance(
            self.scheme, Default
        ):
            raise ValueError("Cannot have both scheme and schemes")
        if not isinstance(self.scheme, Default):
            self.schemes = [self.scheme]
            self.scheme = _default

    def serialize(self) -> Dict[str, Any]:
        return {"security": self.schemes}


# !!!!!!! DICTS !!!!!!! #


class ParameterDict(TypedDict):
    name: str
    in_: ParameterInChoice
    description: NotRequired[str]
    required: NotRequired[bool]
    deprecated: NotRequired[bool]
    allow_empty_value: NotRequired[bool]
    allow_reserved: NotRequired[bool]
    style: NotRequired[ParameterStyleChoice]
    explode: NotRequired[bool]
    schema: NotRequired[Union[Schema, str, float, int, bool, Reference]]
    example: NotRequired[Any]
    examples: NotRequired[List[Dict[str, Union[Example, Reference]]]]


class MediaTypeDict(TypedDict):
    schema: Union[Schema, str, float, int, bool, Reference]
    example: NotRequired[Any]
    examples: NotRequired[List[Dict[str, Union[Example, Reference]]]]
    encoding: NotRequired[Dict[str, Union[Encoding, Reference]]]
