from sanic import Request, Sanic
from sanic.response import text

from sanic_ext import openapi
from sanic_ext.extensions.openapi.definitions import ExternalDocumentation

from .utils import get_spec


def test_external_docs(app: Sanic):
    @app.route("/test0")
    @openapi.document("http://example.com/more", "Find more info here")
    async def handler0(request: Request):
        return text("ok")

    @app.route("/test1")
    @openapi.definition(
        document=ExternalDocumentation("http://example.com/more", "Find more info here")
    )
    async def handler1(request: Request):
        return text("ok")

    @app.route("/test2")
    @openapi.definition(document="http://example.com/more")
    async def handler2(request: Request):
        return text("ok")

    @app.route("/test3")
    async def handler3(request: Request):
        """
        openapi:
        ---
        summary: This is a summary.
        externalDocs:
          description: Find more info here
          url: http://example.com/more
        """
        return text("ok")

    @app.route("/test4")
    @openapi.document(
        ExternalDocumentation("http://example.com/more", "Find more info here")
    )
    async def handler4(request: Request):
        return text("ok")

    spec = get_spec(app)
    paths = spec["paths"]
    assert len(paths) == 5
    for i in range(5):
        doc_obj = paths[f"/test{i}"]["get"]["externalDocs"]
        assert doc_obj["url"] == "http://example.com/more"
        if i != 2:
            assert doc_obj["description"] == "Find more info here"
