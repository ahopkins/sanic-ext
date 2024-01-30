from typing import Optional

from sanic import Sanic  # type: ignore

from .registry import DefinitionRegistry
from .schema import OpenAPI, Paths


class OASBuilder:
    def __init__(self, app: Sanic, paths: Paths):
        self._app = app
        self._registry = DefinitionRegistry()
        self._paths = paths
        self._oas: Optional[OpenAPI] = None

    @property
    def oas(self) -> OpenAPI:
        if not self._oas:
            self._oas = OpenAPI()
        return self._oas

    def build(self):
        self._oas = OpenAPI(
            info={
                "title": self._app.name,
                "version": "0.0.0",
            },
            paths=self._paths,
        )

        from rich import print

        print(self.oas.serialize())
