from dataclasses import dataclass

import pytest
from sanic import Sanic, json


@dataclass
class Foo:
    bar: int


def test_constant_in_registry(app: Sanic):
    assert len(app.ext._constant_registry._registry) == 0
    app.ext.add_constant("bar", 999)
    assert len(app.ext._constant_registry._registry) == 1
    assert "bar" in app.ext._constant_registry


def test_constant_is_injected(app: Sanic):
    app.ext.add_constant("bar", 999)

    @app.get("/")
    async def handler(_, bar: int):
        return json({"bar": bar})

    _, response = app.test_client.get("/")

    assert response.json["bar"] == 999
    assert app.config.BAR == 999


def test_constant_is_injected_into_constructor(app: Sanic):
    app.ext.add_constant("bar", 999)
    app.ext.add_dependency(Foo)

    @app.get("/")
    async def handler(_, foo: Foo):
        return json({"foo": foo.bar})

    _, response = app.test_client.get("/")

    assert response.json["foo"] == 999
    assert app.config.BAR == 999


def test_load_config(app: Sanic):
    app.ext.load_constants()
    assert len(app.ext._constant_registry._registry) == 0
    app.ext.load_constants({**app.config}, overwrite=True)
    assert len(app.ext._constant_registry._registry) == len(
        [k for k in app.config.keys() if k.isupper()]
    )
    assert "request_buffer_size" in app.ext._constant_registry


def test_load_custom(app: Sanic):
    app.ext.load_constants({"foo": "bar"})
    assert len(app.ext._constant_registry._registry) == 1
    assert app.ext._constant_registry.get("foo") == "bar"


def test_load_overwrite(app: Sanic):
    app.ext.load_constants({"foo": "bar"})
    with pytest.raises(ValueError, match="A value for FOO has already been assigned"):
        app.ext.load_constants({"foo": "bar"})
    app.ext.load_constants({"foo": "bar"}, True)
