from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import UUID

import pytest
from sanic.exceptions import SanicException
from sanic.views import HTTPMethodView

from sanic_ext import openapi

from .utils import get_path, get_spec


class Choice(Enum):
    ONE = 1
    TWO = 2


class Bar:
    name: str


class LittleFoo:
    iid: int
    bar: Bar


class BigFoo:
    iid: int
    uid: UUID
    created: date
    updated: datetime
    multi: Union[str, int]
    nullable_single: Optional[bool]
    nullable_multi: Optional[Union[str, int]]
    bar: Bar
    adict: Dict[str, Any]
    bdict: Dict[str, bool]
    anything: Any
    choice: Choice


@pytest.mark.parametrize(
    "args,content_type",
    (
        ((LittleFoo,), "*/*"),
        (({"application/json": LittleFoo},), "application/json"),
        ((openapi.definitions.RequestBody(LittleFoo),), "*/*"),
        (
            (openapi.definitions.RequestBody({"application/json": LittleFoo}),),
            "application/json",
        ),
    ),
)
def test_body_decorator(app, args, content_type):
    @app.route("/")
    @openapi.body(*args, description="something")
    async def handler(_): ...

    spec = get_path(app, "/")

    assert spec["requestBody"]["description"] == "something"

    content = spec["requestBody"]["content"]

    assert content_type in content

    schema = content[content_type]["schema"]

    assert schema["type"] == "object"
    assert schema["properties"]["bar"]["type"] == "object"
    assert schema["properties"]["bar"]["properties"]["name"]["type"] == "string"


@pytest.mark.parametrize("decorator", (openapi.deprecated(), openapi.deprecated))
def test_deprecated_decorator(app, decorator):
    @app.route("/")
    @decorator
    async def handler(_): ...

    spec = get_path(app, "/")
    assert spec["deprecated"]


def test_description_decorator(app):
    @app.route("/")
    @openapi.description("foo")
    async def handler(_): ...

    spec = get_path(app, "/")
    assert spec["description"] == "foo"


@pytest.mark.parametrize(
    "args",
    (
        ("http://example.com/docs",),
        (openapi.definitions.ExternalDocumentation("http://example.com/docs"),),
    ),
)
def test_document_decorator(app, args):
    @app.route("/")
    @openapi.document(*args)
    async def handler(_): ...

    spec = get_path(app, "/")
    assert spec["externalDocs"]["url"] == "http://example.com/docs"


@pytest.mark.parametrize(
    "decorator,excluded",
    (
        (openapi.exclude(), True),
        (openapi.exclude(True), True),
        (openapi.exclude(False), False),
    ),
)
def test_exclude_decorator(app, decorator, excluded):
    @app.route("/")
    @decorator
    async def handler(_): ...

    if excluded:
        with pytest.raises(KeyError):
            get_path(app, "/")
    else:
        get_path(app, "/")


def test_operation_decorator(app):
    @app.route("/")
    @openapi.operation("foo")
    async def handler(_): ...

    spec = get_path(app, "/")
    assert spec["operationId"] == "foo"


@pytest.mark.parametrize(
    "decorator,expected",
    (
        (
            openapi.parameter("thing"),
            {
                "name": "thing",
                "schema": {"type": "string"},
                "in": "query",
            },
        ),
        (
            openapi.parameter("Authorization", str, "header"),
            {
                "name": "Authorization",
                "schema": {"type": "string"},
                "in": "header",
            },
        ),
        (
            openapi.parameter(
                parameter=openapi.definitions.Parameter("foobar", deprecated=True)
            ),
            {
                "name": "foobar",
                "schema": {"type": "string"},
                "deprecated": True,
                "in": "query",
            },
        ),
        (
            openapi.parameter("thing", required=True),
            {
                "name": "thing",
                "schema": {"type": "string"},
                "required": True,
                "in": "query",
            },
        ),
    ),
)
def test_parameter_decorator(app, decorator, expected):
    @app.route("/")
    @decorator
    def handler_one(_): ...

    parameters = get_path(app, "/")["parameters"]
    assert parameters[0] == expected


@pytest.mark.parametrize(
    "decorator,expected",
    (
        (
            openapi.response(),
            {
                "default": {
                    "content": {"*/*": {"schema": {"type": "string"}}},
                    "description": "Default Response",
                }
            },
        ),
        (
            openapi.response(200, str, "foobar"),
            {
                "200": {
                    "content": {"*/*": {"schema": {"type": "string"}}},
                    "description": "foobar",
                }
            },
        ),
        (
            openapi.response(200, Bar, "..."),
            {
                "200": {
                    "content": {
                        "*/*": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}},
                            }
                        }
                    },
                    "description": "...",
                }
            },
        ),
        (
            openapi.response(content={"application/json": Bar}, description="..."),
            {
                "default": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}},
                            }
                        }
                    },
                    "description": "...",
                }
            },
        ),
        (
            openapi.response(
                response=openapi.definitions.Response(
                    {"application/json": Bar}, description="...", status=201
                )
            ),
            {
                "201": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}},
                            }
                        }
                    },
                    "description": "...",
                }
            },
        ),
        (
            openapi.response(content={"application/json": BigFoo}),
            {
                "default": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "iid": {
                                        "type": "integer",
                                        "format": "int32",
                                    },
                                    "uid": {
                                        "type": "string",
                                        "format": "uuid",
                                    },
                                    "created": {
                                        "type": "string",
                                        "format": "date",
                                    },
                                    "updated": {
                                        "type": "string",
                                        "format": "date-time",
                                    },
                                    "multi": {
                                        "oneOf": [
                                            {"type": "string"},
                                            {
                                                "type": "integer",
                                                "format": "int32",
                                            },
                                        ]
                                    },
                                    "nullable_single": {
                                        "type": "boolean",
                                        "nullable": True,
                                    },
                                    "nullable_multi": {
                                        "nullable": True,
                                        "oneOf": [
                                            {
                                                "type": "string",
                                            },
                                            {
                                                "type": "integer",
                                                "format": "int32",
                                            },
                                        ],
                                    },
                                    "bar": {
                                        "type": "object",
                                        "properties": {"name": {"type": "string"}},
                                    },
                                    "adict": {
                                        "type": "object",
                                        "additionalProperties": {},
                                    },
                                    "bdict": {
                                        "type": "object",
                                        "additionalProperties": {"type": "boolean"},
                                    },
                                    "anything": {},
                                    "choice": {
                                        "type": "integer",
                                        "format": "int32",
                                        "enum": [1, 2],
                                    },
                                },
                            }
                        }
                    },
                    "description": "Default Response",
                }
            },
        ),
    ),
)
def test_response_decorator(app, decorator, expected):
    @app.route("/")
    @decorator
    def handler_one(_): ...

    responses = get_path(app, "/")["responses"]
    assert responses == expected


def test_summary_decorator(app):
    @app.route("/")
    @openapi.summary("foo")
    async def handler(_): ...

    spec = get_path(app, "/")
    assert spec["summary"] == "foo"


@pytest.mark.parametrize(
    "decorator,tags",
    (
        (openapi.tag("foo"), ("foo",)),
        (openapi.tag("foo", openapi.definitions.Tag("bar")), ("foo", "bar")),
    ),
)
def test_tag_decorator(app, decorator, tags):
    @app.route("/")
    @decorator
    def handler_one(_): ...

    spec = get_spec(app)
    for tag in tags:
        assert {"name": tag} in spec["tags"]

    tagged = get_path(app, "/")["tags"]
    assert list(tagged) == list(tags)


def test_definition_decorator_body_dict_w_obj(app):
    @app.route("/")
    @openapi.definition(body={"application/json": Bar})
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }


def test_definition_decorator_body_dict_only_schema_head(app):
    @app.route("/")
    @openapi.definition(
        body={
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    )
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }


def test_definition_decorator_body_dict_types_schema_head(app):
    @app.route("/")
    @openapi.definition(body={"application/json": {"schema": {"name": str}}})
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }


def test_definition_decorator_body_dict_only_schema_root(app):
    @app.route("/")
    @openapi.definition(
        body={
            "application/json": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            }
        }
    )
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }


def test_definition_decorator_body_dict_types_schema_root(app):
    @app.route("/")
    @openapi.definition(body={"application/json": {"name": str}})
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }


def test_definition_decorator_httpmethodview(app):
    class View(HTTPMethodView, uri="/", attach=app):
        @openapi.definition(body={"application/json": Bar})
        async def get(self, request): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }


def test_definition_decorator_body_dict_multi(app):
    @app.route("/")
    @openapi.definition(body={"application/json": Bar, "text/plain": str})
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            },
            "text/plain": {"schema": {"type": "string"}},
        }
    }


def test_definition_decorator_body_request_body(app):
    @app.route("/")
    @openapi.definition(body=openapi.definitions.RequestBody(str, required=True))
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {"*/*": {"schema": {"type": "string"}}},
        "required": True,
    }


def test_definition_decorator_body_model(app):
    @app.route("/")
    @openapi.definition(body=Bar)
    async def handler(_): ...

    body = get_path(app, "/")["requestBody"]
    assert body == {
        "content": {
            "*/*": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }


def test_definition_decorator_deprecated(app):
    @app.route("/")
    @openapi.definition(deprecated=True)
    async def handler(_): ...

    assert get_path(app, "/")["deprecated"]


def test_definition_decorator_description(app):
    @app.route("/")
    @openapi.definition(description="foo")
    async def handler(_): ...

    assert get_path(app, "/")["description"] == "foo"


def test_definition_decorator_document_string(app):
    @app.route("/")
    @openapi.definition(document="foo")
    async def handler(_): ...

    assert get_path(app, "/")["externalDocs"] == {"url": "foo"}


def test_definition_decorator_document_obj(app):
    @app.route("/")
    @openapi.definition(
        document=openapi.definitions.ExternalDocumentation("foo", "bar")
    )
    async def handler(_): ...

    assert get_path(app, "/")["externalDocs"] == {
        "url": "foo",
        "description": "bar",
    }


def test_definition_decorator_operation(app):
    @app.route("/")
    @openapi.definition(operation="foo")
    async def handler(_): ...

    assert get_path(app, "/")["operationId"] == "foo"


def test_definition_decorator_parameter_string(app):
    @app.route("/")
    @openapi.definition(parameter="foo")
    async def handler(_): ...

    parameters = get_path(app, "/")["parameters"]
    assert {
        "name": "foo",
        "schema": {"type": "string"},
        "in": "query",
    } in parameters


def test_definition_decorator_parameter_dict(app):
    @app.route("/")
    @openapi.definition(parameter={"name": "foo"})
    async def handler(_): ...

    parameters = get_path(app, "/")["parameters"]
    assert {
        "name": "foo",
        "schema": {"type": "string"},
        "in": "query",
    } in parameters


def test_definition_decorator_parameter_obj(app):
    @app.route("/")
    @openapi.definition(
        parameter=openapi.definitions.Parameter("foo", description="bar")
    )
    async def handler(_): ...

    parameters = get_path(app, "/")["parameters"]
    assert {
        "name": "foo",
        "schema": {"type": "string"},
        "in": "query",
        "description": "bar",
    } in parameters


def test_definition_decorator_parameter_string_multi(app):
    @app.route("/")
    @openapi.definition(parameter=["foo", "bar"])
    async def handler(_): ...

    parameters = get_path(app, "/")["parameters"]
    assert {
        "name": "foo",
        "schema": {"type": "string"},
        "in": "query",
    } in parameters
    assert {
        "name": "bar",
        "schema": {"type": "string"},
        "in": "query",
    } in parameters


def test_definition_decorator_parameter_dict_multi(app):
    @app.route("/")
    @openapi.definition(
        parameter=[{"name": "foo"}, {"name": "bar", "location": "header"}]
    )
    async def handler(_): ...

    parameters = get_path(app, "/")["parameters"]
    assert {
        "name": "foo",
        "schema": {"type": "string"},
        "in": "query",
    } in parameters
    assert {
        "name": "bar",
        "schema": {"type": "string"},
        "in": "header",
    } in parameters


def test_definition_decorator_parameter_obj_multi(app):
    @app.route("/")
    @openapi.definition(
        parameter=[
            openapi.definitions.Parameter("foo"),
            openapi.definitions.Parameter("bar"),
        ]
    )
    async def handler(_): ...

    parameters = get_path(app, "/")["parameters"]
    assert {
        "name": "foo",
        "schema": {"type": "string"},
        "in": "query",
    } in parameters
    assert {
        "name": "bar",
        "schema": {"type": "string"},
        "in": "query",
    } in parameters


def test_definition_decorator_response_dict(app):
    @app.route("/")
    @openapi.definition(response={"application/json": Bar})
    async def handler(_): ...

    responses = get_path(app, "/")["responses"]
    assert responses["default"] == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        },
        "description": "Default Response",
    }


def test_definition_decorator_response_obj(app):
    @app.route("/")
    @openapi.definition(
        response=openapi.definitions.Response({"application/json": Bar}, status=201)
    )
    async def handler(_): ...

    responses = get_path(app, "/")["responses"]
    assert responses["201"] == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        },
        "description": "Default Response",
    }


def test_definition_decorator_response_model(app):
    @app.route("/")
    @openapi.definition(response=Bar)
    async def handler(_): ...

    responses = get_path(app, "/")["responses"]
    assert responses["default"] == {
        "content": {
            "*/*": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        },
        "description": "Default Response",
    }


def test_definition_decorator_response_dict_multi(app):
    @app.route("/")
    @openapi.definition(
        response=[
            {"application/json": Bar, "text/plain": str},
            {"text/html": str},
        ]
    )
    async def handler(_): ...

    responses = get_path(app, "/")["responses"]

    assert responses["default"] == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            },
            "text/plain": {"schema": {"type": "string"}},
            "text/html": {"schema": {"type": "string"}},
        },
        "description": "Default Response",
    }


def test_definition_decorator_response_obj_multi(app):
    @app.route("/")
    @openapi.definition(
        response=[
            openapi.definitions.Response({"application/json": Bar}, status=201),
            openapi.definitions.Response(
                {"*/*": str}, status=400, description="Something bad"
            ),
        ]
    )
    async def handler(_): ...

    responses = get_path(app, "/")["responses"]
    assert responses["201"] == {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        },
        "description": "Default Response",
    }
    assert responses["400"] == {
        "content": {"*/*": {"schema": {"type": "string"}}},
        "description": "Something bad",
    }


def test_definition_decorator_response_model_multi(app):
    with pytest.raises(SanicException):

        @app.route("/")
        @openapi.definition(response=[Bar, LittleFoo])
        async def handler(_): ...


def test_definition_decorator_summary(app):
    @app.route("/")
    @openapi.definition(summary="foo")
    async def handler(_): ...

    assert get_path(app, "/")["summary"] == "foo"


def test_definition_decorator_tag_string(app):
    @app.route("/")
    @openapi.definition(tag="foo")
    async def handler(_): ...

    assert list(get_path(app, "/")["tags"]) == ["foo"]


def test_definition_decorator_tag_obj(app):
    @app.route("/")
    @openapi.definition(tag=openapi.definitions.Tag("foo"))
    async def handler(_): ...

    assert list(get_path(app, "/")["tags"]) == ["foo"]


def test_definition_decorator_tag_string_multi(app):
    @app.route("/")
    @openapi.definition(tag=["foo", "bar"])
    async def handler(_): ...

    assert list(get_path(app, "/")["tags"]) == ["foo", "bar"]


def test_definition_decorator_tag_obj_multi(app):
    @app.route("/")
    @openapi.definition(
        tag=[openapi.definitions.Tag("foo"), openapi.definitions.Tag("bar")]
    )
    async def handler(_): ...

    assert list(get_path(app, "/")["tags"]) == ["foo", "bar"]
