"""
Classes defined from the OpenAPI 3.0 specifications.

I.e., the objects described https://swagger.io/docs/specification

"""

from __future__ import annotations

from inspect import isclass
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
    get_type_hints,
)

from sanic.exceptions import SanicException

from sanic_ext.utils.typing import (
    contains_annotations,
    is_msgspec,
    is_pydantic,
)

from .types import Definition, Schema


class Reference(Schema):
    def __init__(self, value):
        super().__init__(**{"$ref": value})

    def guard(self, fields: Dict[str, Any]):
        return fields


class Contact(Definition):
    name: str
    url: str
    email: str


class License(Definition):
    name: str
    url: str

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)


class Info(Definition):
    title: str
    description: str
    termsOfService: str
    contact: Contact
    license: License
    version: str

    def __init__(self, title: str, version: str, **kwargs):
        super().__init__(title=title, version=version, **kwargs)


class Example(Definition):
    summary: str
    description: str
    value: Any
    externalValue: str

    def __init__(self, value: Any = None, **kwargs):
        super().__init__(value=value, **kwargs)

    @staticmethod
    def make(value: Any, **kwargs):
        return Example(Schema.make(value), **kwargs)

    @staticmethod
    def external(value: Any, **kwargs):
        return Example(externalValue=value, **kwargs)


class MediaType(Definition):
    schema: Schema
    example: Any

    def __init__(self, schema: Union[Schema, Dict[str, Any]], **kwargs):
        if isinstance(schema, dict) and contains_annotations(schema):
            schema = Schema.make(schema)
        super().__init__(schema=schema, **kwargs)

    @staticmethod
    def make(value: Any):
        if isinstance(value, dict):
            kwargs = {}
            if "schema" in value:
                kwargs = {**value}
                value = kwargs.pop("schema")
            return MediaType(value, **kwargs)
        # See https://github.com/sanic-org/sanic-ext/issues/152
        # The following lines will automatically inject pydantic models as
        # components if that feature is desired. Until that decision is made
        # this commented out code will remain.
        # elif isclass(value) and is_pydantic(value):
        #     return MediaType(Component(value))
        return MediaType(Schema.make(value))

    @staticmethod
    def all(content: Any):
        media_types = (
            content if isinstance(content, dict) else {"*/*": content or {}}
        )

        return {x: MediaType.make(v) for x, v in media_types.items()}


class Response(Definition):
    content: Union[Any, Dict[str, Union[Any, MediaType]]]
    description: Optional[str]
    status: Union[Literal["default"], int]

    __nullable__ = None
    __ignore__ = ["status"]

    def __init__(
        self,
        content: Optional[Union[Any, Dict[str, Union[Any, MediaType]]]] = None,
        status: Union[Literal["default"], int] = "default",
        description: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            content=content,
            status=status,
            description=description,
            **kwargs,
        )

    @staticmethod
    def make(content, description: Optional[str] = None, **kwargs):
        if not description:
            description = "Default Response"

        return Response(
            MediaType.all(content), description=description, **kwargs
        )


class RequestBody(Definition):
    description: Optional[str]
    required: Optional[bool]
    content: Union[Any, Dict[str, Union[Any, MediaType]]]

    __nullable__ = None

    def __init__(
        self,
        content: Union[Any, Dict[str, Union[Any, MediaType]]],
        required: Optional[bool] = None,
        description: Optional[str] = None,
        **kwargs,
    ):
        """Can be initialized with content in one of a few ways:

        RequestBody(SomeModel)
        RequestBody({"application/json": SomeModel})
        RequestBody({"application/json": {"name": str}})
        """
        super().__init__(
            content=content,
            required=required,
            description=description,
            **kwargs,
        )

    @staticmethod
    def make(content: Any, **kwargs):
        return RequestBody(MediaType.all(content), **kwargs)


class ExternalDocumentation(Definition):
    url: str
    description: str

    __nullable__ = None

    def __init__(self, url: str, description=None):
        super().__init__(url=url, description=description)

    @staticmethod
    def make(url: str, description: Optional[str] = None):
        return ExternalDocumentation(url, description)


class Header(Definition):
    name: str
    description: str
    externalDocs: ExternalDocumentation

    def __init__(self, url: str, description=None):
        super().__init__(url=url, description=description)

    @staticmethod
    def make(url: str, description: Optional[str] = None):
        return Header(url, description)


class Parameter(Definition):
    name: str
    schema: Union[Type, Schema]
    location: str
    description: Optional[str]
    required: Optional[bool]
    deprecated: Optional[bool]
    allowEmptyValue: Optional[bool]

    __nullable__ = None

    def __init__(
        self,
        name: str,
        schema: Union[Type, Schema] = str,
        location: str = "query",
        description: Optional[str] = None,
        required: Optional[bool] = None,
        deprecated: Optional[bool] = None,
        allowEmptyValue: Optional[bool] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            schema=schema,
            location=location,
            description=description,
            required=required,
            deprecated=deprecated,
            allowEmptyValue=allowEmptyValue,
            **kwargs,
        )

    @property
    def fields(self):
        values = super().fields

        if "location" in values:
            values["in"] = values.pop("location")

        return values

    @staticmethod
    def make(name: str, schema: type, location: str, **kwargs):
        if location == "path" and "required" not in kwargs:
            kwargs["required"] = True

        return Parameter(name, Schema.make(schema), location, **kwargs)


class Operation(Definition):
    tags: List[str]
    summary: str
    description: str
    operationId: str
    requestBody: RequestBody
    externalDocs: ExternalDocumentation
    parameters: List[Parameter]
    responses: Dict[str, Response]
    security: Dict[str, List[str]]
    callbacks: List[str]  # TODO
    deprecated: bool
    servers: List[Dict[str, str]]


class PathItem(Definition):
    summary: str
    description: str
    get: Operation
    put: Operation
    post: Operation
    delete: Operation
    options: Operation
    head: Operation
    patch: Operation
    trace: Operation


class Flow(Definition):
    authorizationUrl: str
    tokenUrl: str
    refreshUrl: str
    scopes: Dict[str, str]


class Flows(Definition):
    implicit: Flow
    password: Flow
    clientCredentials: Flow
    authorizationCode: Flow


class SecurityRequirement(Definition):
    name: str
    value: List[str]


class SecurityScheme(Definition):
    type: str
    bearerFormat: str
    description: str
    flows: Flows
    location: str
    name: str
    openIdConnectUrl: str
    scheme: str

    __nullable__ = None

    def __init__(self, type: str, **kwargs):
        super().__init__(type=type, **kwargs)

    @property
    def fields(self):
        values = super().fields

        if "location" in values:
            values["in"] = values.pop("location")

        return values

    @staticmethod
    def make(_type: str, cls: Type, **kwargs):
        params: Dict[str, Any] = getattr(cls, "__dict__", {})
        return SecurityScheme(_type, **params, **kwargs)


class ServerVariable(Definition):
    default: str
    description: str
    enum: List[str]

    def __init__(self, default: str, **kwargs):
        super().__init__(default=default, **kwargs)


class Server(Definition):
    url: str
    description: str
    variables: Dict[str, ServerVariable]

    __nullable__ = None

    def __init__(
        self,
        url: str,
        description: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            url=url, description=description, variables=variables or {}
        )


class Tag(Definition):
    name: str
    description: str
    externalDocs: ExternalDocumentation

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)


class Components(Definition):
    # This class is not being used in sanic-openapi right now, but the
    # definition is kept here to keep in close accordance with the openapi
    # spec, in case it is desired to be added later.
    schemas: Dict[str, Schema]
    responses: Dict[str, Response]
    parameters: Dict[str, Parameter]
    examples: Dict[str, Example]
    requestBodies: Dict[str, RequestBody]
    headers: Dict[str, Header]
    securitySchemes: Dict[str, SecurityScheme]
    links: Dict[str, Schema]  # TODO
    callbacks: Dict[str, Schema]  # TODO


def Component(
    obj: Any, *, name: str = "", field: str = "schemas"
) -> Reference:
    hints = get_type_hints(Components)

    if field not in hints:
        raise AttributeError(
            f"Unknown field '{field}'. Must be a valid field per OAS3 "
            "requirements. See "
            "https://swagger.io/specification/#components-object."
        )

    if not isclass(obj) and not name:
        raise SanicException(
            f"Components {obj} must be created with a declared name"
        )

    if not name:
        name = obj.__name__

    from sanic_ext.extensions.openapi.builders import SpecificationBuilder

    spec = SpecificationBuilder()
    refval = f"#/components/{field}/{name}"
    ref = Reference(refval)

    if not spec.has_component(field, name):
        prop_info = hints[field]
        type_ = prop_info.__args__[1]
        if is_msgspec(obj):
            import msgspec

            _, definitions = msgspec.json.schema_components(
                [obj], ref_template="#/components/schemas/{name}"
            )
            if definitions:
                for key, value in definitions.items():
                    spec.add_component(field, key, value)
        elif is_pydantic(obj):
            try:
                schema = obj.model_json_schema
            except AttributeError:
                schema = obj.__pydantic_model__.model_json_schema
            component = schema(ref_template="#/components/schemas/{model}")
            definitions = component.pop("definitions", None)
            if definitions:
                for key, value in definitions.items():
                    spec.add_component(field, key, value)
            spec.add_component(field, name, component)
        else:
            component = (
                type_.make(obj) if hasattr(type_, "make") else type_(obj)
            )
            spec.add_component(field, name, component)

    return ref


class OpenAPI(Definition):
    openapi: str
    info: Info
    servers: List[Server]
    paths: Dict[str, PathItem]
    components: Components
    security: Dict[str, SecurityScheme]
    tags: List[Tag]
    externalDocs: ExternalDocumentation

    def __init__(self, info: Info, paths: Dict[str, PathItem], **kwargs):
        use = {k: v for k, v in kwargs.items() if v is not None}
        super().__init__(openapi="3.0.3", info=info, paths=paths, **use)
