from sanic import Sanic  # type: ignore

from sanic_ext.extensions.oas.builder import OASBuilder
from sanic_ext.extensions.oas.registry import DefinitionRegistry

from .schema import Path, Paths


async def _build(app: Sanic):
    registry = DefinitionRegistry()

    paths = Paths()

    for route in app.router.routes:
        wrapped = getattr(route.handler, "__wrapped__", None)
        if not wrapped and getattr(route.handler, "view_class", None):
            if len(route.methods) > 1:
                raise Exception
            wrapped = getattr(
                route.handler.view_class, tuple(route.methods)[0].lower(), None
            )
        if wrapped:
            key = f"{wrapped.__module__}.{wrapped.__qualname__}"
            if definition := registry.get(key):
                for method in route.methods:
                    paths.register(Path(route, method, definition))
    app.ctx._oas_builder = OASBuilder(app, paths)
    app.ctx._oas_builder.build()


def build_spec(app: Sanic):
    app.after_server_start(_build)
