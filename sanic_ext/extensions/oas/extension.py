from ..base import Extension
from .startup import build_spec


class OASExtension(Extension):
    name = "oas"

    def startup(self, bootstrap) -> None:
        if self.app.config.OAS:
            bootstrap.oas = None
            build_spec(self.app)
