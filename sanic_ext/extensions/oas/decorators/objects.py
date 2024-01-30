from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints

from ..definition import Definition
from ..signature import (
    Deprecated,
    ExternalDocument,
    Parameter,
    ParameterDict,
    Reference,
    RequestBody,
    Response,
    ResponseReference,
    SecurityScheme,
    Text,
)


@dataclass
class tags(Definition):
    values: List[str]

    class Meta:
        merge = True

    def merge(self, target: tags) -> None:
        self.values.extend(tags.values)

    def serialize(self) -> Dict[str, Any]:
        return {"tags": self.values}


@dataclass
class tag(Text, Definition):
    def setup(self):
        tags([self.text])(self._func)


@dataclass
class summary(Text, Definition):
    ...


@dataclass
class description(Text, Definition):
    ...


@dataclass
class external_docs(Definition):
    documents: List[ExternalDocument]

    class Meta:
        merge = True

    def merge(self, target: external_docs) -> None:
        self.documents.extend(target.documents)


@dataclass
class external_doc(ExternalDocument, Definition):
    def setup(self):
        external_docs([self])(self._func)


document = external_doc


@dataclass
class operation_id(Text, Definition):
    ...


@dataclass
class parameters(Definition):  # TODO: Reference
    values: List[Union[Parameter, Reference, ParameterDict]] = field(
        default_factory=list
    )
    model: Optional[Type] = None

    class Meta:
        merge = True

    def merge(self, target: parameters) -> None:
        names = [
            name for val in self.values if (name := getattr(val, "name", None))
        ]
        self.values.extend(
            [
                Parameter(**value) if isinstance(value, dict) else value
                for value in target.values
                if (
                    (isinstance(value, Parameter) and value.name not in names)
                    or (isinstance(value, dict) and value["name"] not in names)
                    # TODO: dedupe references
                    or isinstance(value, Reference)
                )
            ]
        )

    def __post_init__(self):
        self.values = [self.parameterize(val) for val in self.values]
        if self.model:
            self.values.extend(
                [
                    Parameter(name=name, schema=schema)
                    for name, schema in get_type_hints(self.model).items()
                ]
            )

    def serialize(self) -> Dict[str, Any]:
        return {
            "parameters": [
                val if isinstance(val, dict) else val.serialize()
                for val in self.values
            ]
        }

    @staticmethod
    def parameterize(item: Any) -> Parameter:
        if isinstance(item, Parameter):
            return item
        elif isinstance(item, dict):
            return Parameter(**item)
        # TODO: Reference
        else:
            raise TypeError(
                f"Expected Parameter or dict, got {type(item).__name__}"
            )


@dataclass
class parameter(Parameter, Definition):
    def setup(self):
        parameters([self])(self._func)


@dataclass
class request_body(RequestBody, Reference, Definition):  # TODO
    ...


body = request_body


@dataclass
class responses(Definition):
    values: List[Union[Response, ResponseReference]]

    class Meta:
        merge = True

    def merge(self, target: responses) -> None:
        self.values.extend(target.values)

    def serialize(self) -> Dict[str, Any]:
        return {
            "responses": {
                "default"
                if isinstance(val, dict)
                else val.status: val
                if isinstance(val, dict)
                else val.serialize()
                for val in self.values
            }
        }


@dataclass
class response(Response, Definition):
    def setup(self):
        responses(values=[self])(self._func)


@dataclass
class callbacks(Definition):  # TODO
    ...


@dataclass
class deprecated(Deprecated, Definition):
    ...


@dataclass
class security(SecurityScheme, Definition):
    ...


@dataclass
class servers(Definition):  # TODO
    ...
