from sanic import Sanic
from sanic.response import text

from sanic_ext import openapi

from .utils import get_spec


def test_func_handlers(app: Sanic):
    class TestClass:
        @staticmethod
        @openapi.definition(
            summary="staticmethod custom summary",
            tag="Test",
        )
        async def staticmethod_handler(request):
            return text("...")

        @classmethod
        @openapi.definition(
            summary="classmethod custom summary",
            tag="Test",
        )
        async def classmethod_handler(cls, request):
            return text("...")

        @openapi.definition(
            summary="instance method custom summary",
            tag="Test",
        )
        async def instance_method_handler(self, request):
            return text("...")

    app.add_route(TestClass.staticmethod_handler, "/staticmethod")
    app.add_route(TestClass.classmethod_handler, "/classmethod")
    app.add_route(TestClass().instance_method_handler, "/instance_method")

    spec = get_spec(app)
    paths = spec["paths"]
    assert len(paths) == 3
    assert paths["/staticmethod"]["get"]["summary"] == "staticmethod custom summary"
    assert paths["/classmethod"]["get"]["summary"] == "classmethod custom summary"
    assert (
        paths["/instance_method"]["get"]["summary"] == "instance method custom summary"
    )
