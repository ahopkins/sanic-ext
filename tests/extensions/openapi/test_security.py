from sanic import Sanic

from sanic_ext import openapi
from tests.extensions.openapi.utils import get_path, get_spec


def test_secured(app: Sanic):
    @app.route("/one")
    async def handler1(request):
        """
        openapi:
        ---
        security:
            - foo: []
        """

    @app.route("/two")
    @openapi.secured("foo")
    @openapi.secured({"bar": []})
    @openapi.secured(baz=[])
    async def handler2(request): ...

    @app.route("/three")
    @openapi.definition(secured="foo")
    @openapi.definition(secured={"bar": []})
    async def handler3(request): ...

    spec = get_path(app, "/one")
    assert {"foo": []} in spec["security"]

    spec = get_path(app, "/two")
    assert {"foo": []} in spec["security"]
    assert {"bar": []} in spec["security"]
    assert {"baz": []} in spec["security"]

    spec = get_path(app, "/three")
    assert {"foo": []} in spec["security"]
    assert {"bar": []} in spec["security"]


def test_security_scheme(app: Sanic):
    app.ext.openapi.add_security_scheme("api_key", "apiKey")
    app.ext.openapi.add_security_scheme("token1", "http")
    app.ext.openapi.add_security_scheme(
        "token2", "http", scheme="bearer", bearer_format="JWT"
    )
    app.ext.openapi.add_security_scheme("oldschool", "http", scheme="basic")
    app.ext.openapi.add_security_scheme(
        "oa2",
        "oauth2",
        flows={
            "implicit": {
                "authorizationUrl": "http://example.com/auth",
                "scopes": {
                    "one:two": "something",
                    "three:four": "something else",
                },
            }
        },
    )

    spec = get_spec(app)
    schemes = spec["components"]["securitySchemes"]

    assert schemes["api_key"] == {
        "type": "apiKey",
        "name": "authorization",
        "in": "header",
    }
    assert schemes["token1"] == {
        "type": "http",
        "scheme": "Bearer",
    }
    assert schemes["token2"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert schemes["oa2"] == {
        "type": "oauth2",
        "flows": {
            "implicit": {
                "authorizationUrl": "http://example.com/auth",
                "scopes": {
                    "one:two": "something",
                    "three:four": "something else",
                },
            }
        },
    }


def test_raw(app: Sanic):
    app.ext.openapi.raw({"security": [{}, {"foo": []}]})

    spec = get_spec(app)
    assert {} in spec["security"]
    assert {"foo": []} in spec["security"]
