import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, List

from sanic.constants import HTTPMethod
from sanic_routing.route import Route

from .decorators.objects import parameters
from .definition import Definition, Serializable
from .signature import Parameter, ParameterInChoice, SecurityScheme


@dataclass
class Path:
    route: Route
    method: HTTPMethod
    definitions: List[Definition] = field(default_factory=list)
    _PATTERN = re.compile(
        r"<(?P<name>[a-zA-Z0-9_]+)(?::(?P<type>[a-zA-Z0-9_]+))?>"
    )

    def __post_init__(self):
        parameters(
            values=[
                Parameter(
                    name=param.name,
                    in_=ParameterInChoice.PATH,
                    schema=param.cast,
                )
                for param in self.route.defined_params.values()
            ]
        )(self.route.handler)

    @cached_property
    def uri(self) -> str:
        return self._convert_uri(self.route.uri)

    def _convert_uri(self, uri: str) -> str:
        return self._PATTERN.sub(r"{\g<name>}", uri)


@dataclass
class Paths:
    _items: List[Path] = field(default_factory=list)

    def register(self, item: Path) -> None:
        self._items.append(item)

    def serialize(self) -> dict[str, Any]:
        output: dict[str, Any] = {}

        for item in self._items:
            uri = item.uri
            path_params = [
                param.name for param in item.route.defined_params.values()
            ]
            output.setdefault(uri, {})
            for definition in item.definitions:
                output[uri].setdefault(item.method.lower(), {})
                output[uri][item.method.lower()].update(definition.serialize())

                # Since OAS definitions need to be added using the handler,
                # when multiple route definitions are on a single handler it
                # is possible for path params to be defined on the handler
                # that are not in the route definition. Therefore we need to
                # remove any path params that are not defined in the route.
                if "parameters" in output[uri][item.method.lower()]:
                    output[uri][item.method.lower()]["parameters"] = [
                        param
                        for param in output[uri][item.method.lower()][
                            "parameters"
                        ]
                        if param["in"] != "path"
                        or param["name"] in path_params
                    ]

            if "responses" not in output[uri][item.method.lower()]:
                output[uri][item.method.lower()]["responses"] = {
                    "default": {"description": "Default response"}
                }

        return output


@dataclass
class Components:
    schemas: dict[str, Any] = field(default_factory=dict)
    security_schemes: list[dict[str, Any]] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    responses: dict[str, Any] = field(default_factory=dict)
    requestBodies: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, Any] = field(default_factory=dict)
    examples: dict[str, Any] = field(default_factory=dict)
    links: dict[str, Any] = field(default_factory=dict)
    callbacks: dict[str, Any] = field(default_factory=dict)
    path_items: dict[str, Any] = field(default_factory=dict)

    def serialize(self) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if value:
                output[key] = (
                    value.serialize()
                    if isinstance(value, Serializable)
                    else value
                )
        return output


@dataclass
class OpenAPI(Serializable):
    openapi: str = "3.0.3"
    info: dict[str, Any] = field(default_factory=dict)
    paths: Paths = field(default_factory=Paths)
    components: Components = field(default_factory=Components)
