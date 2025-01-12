import pytest
from sanic import Sanic
from sanic.response import empty, text

from sanic_ext.bootstrap import Extend


def test_trace_and_connect_available(app: Sanic):
    @app.route("/", methods=["trace", "connect"])
    async def handler(_):
        return empty()

    _, response = app.test_client.request("", http_method="trace")
    assert response.status == 204
    _, response = app.test_client.request("", http_method="connect")
    assert response.status == 204
    _, response = app.test_client.request("", http_method="get")
    assert response.status == 405


def test_auto_head(app: Sanic, get_docs):
    app.config.TOUCHUP = False

    @app.get("/foo")
    async def foo_handler(_):
        return text("...")

    assert app.config.HTTP_AUTO_HEAD
    _, response = app.test_client.head("/foo")
    assert response.status == 200
    assert len(response.body) == 0
    assert int(response.headers["content-length"]) == 3

    schema = get_docs()
    assert "get" in schema["paths"]["/foo"]


def test_auto_options(app: Sanic, get_docs):
    @app.post("/foo")
    async def foo_handler(_):
        return text("...")

    _, response = app.test_client.options("/foo")
    assert response.status == 204
    assert len(response.body) == 0
    assert "POST" in response.headers["allow"]
    assert "OPTIONS" in response.headers["allow"]

    schema = get_docs()
    assert "post" in schema["paths"]["/foo"]


def test_auto_trace(bare_app: Sanic):
    Extend(bare_app, config={"http_auto_trace": True})

    @bare_app.get("/foo")
    async def foo_handler(_):
        return text("...")

    request, response = bare_app.test_client.request("/foo", http_method="trace")
    assert response.status == 200
    assert response.body.startswith(request.head)


def test_auto_head_with_vhosts(app: Sanic, get_docs):
    @app.get("/foo", host="one.com", name="one")
    async def foo_handler_one(_):
        return text(".")

    @app.get("/foo", host="two.com", name="two")
    async def foo_handler_two(_):
        return text("..")

    assert app.config.HTTP_AUTO_HEAD
    _, response = app.test_client.head("/foo", headers={"host": "one.com"})
    assert response.status == 200
    assert len(response.body) == 0
    assert int(response.headers["content-length"]) == 1

    _, response = app.test_client.head("/foo", headers={"host": "two.com"})
    assert response.status == 200
    assert len(response.body) == 0
    assert int(response.headers["content-length"]) == 2

    schema = get_docs()
    assert "get" in schema["paths"]["/foo"]


def test_auto_options_with_vhosts(app: Sanic, get_docs):
    @app.post("/foo", host="one.com", name="one")
    async def foo_handler_one(_):
        return text(".")

    @app.post("/foo", host="two.com", name="two")
    async def foo_handler_two(_):
        return text("..")

    assert app.config.HTTP_AUTO_OPTIONS
    _, response = app.test_client.options("/foo", headers={"host": "one.com"})
    assert response.status == 204
    assert len(response.body) == 0
    assert "POST" in response.headers["allow"]
    assert "OPTIONS" in response.headers["allow"]

    _, response = app.test_client.options("/foo", headers={"host": "two.com"})
    assert response.status == 204
    assert len(response.body) == 0
    assert "POST" in response.headers["allow"]
    assert "OPTIONS" in response.headers["allow"]


# This test also appears in Core Sanic tests but is added here as well
# because of: https://github.com/sanic-org/sanic-ext/issues/148
@pytest.mark.parametrize("unquote", [True, False, None])
def test_unquote_add_route(app, unquote):
    async def handler1(_, foo):
        return text(foo)

    app.add_route(handler1, "/<foo>", unquote=unquote)
    value = "啊" if unquote else r"%E5%95%8A"

    _, response = app.test_client.get("/啊")
    assert response.text == value

    _, response = app.test_client.get(r"/%E5%95%8A")
    assert response.text == value
