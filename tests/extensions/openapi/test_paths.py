import pytest
from sanic import Sanic

from .utils import get_spec


@pytest.fixture(autouse=True)
def handlers(app: Sanic):
    @app.route("/test1")
    async def handler1(_): ...

    @app.route("/test2/1")
    async def handler2(_): ...

    @app.route("/test3/")
    async def handler3(_): ...

    @app.route("/test4/2/")
    async def handler4(_): ...


def test_paths_with_all_uri_filter(app: Sanic):
    app.config.API_URI_FILTER = "all"

    spec = get_spec(app)
    assert list(spec["paths"].keys()) == [
        "/test1",
        "/test1/",
        "/test2/1",
        "/test2/1/",
        "/test3",
        "/test3/",
        "/test4/2",
        "/test4/2/",
    ]


def test_paths_with_slash_uri_filter(app: Sanic):
    app.config.API_URI_FILTER = "slash"
    spec = get_spec(app)

    assert list(spec["paths"].keys()) == [
        "/test1/",
        "/test2/1/",
        "/test3/",
        "/test4/2/",
    ]


def test_paths_without_uri_filter(app: Sanic):
    spec = get_spec(app)
    assert list(spec["paths"].keys()) == [
        "/test1",
        "/test2/1",
        "/test3",
        "/test4/2",
    ]
