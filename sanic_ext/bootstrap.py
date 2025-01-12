from __future__ import annotations

import os

from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Type, Union
from warnings import warn

from sanic import Sanic, __version__
from sanic.config import DEFAULT_CONFIG
from sanic.exceptions import SanicException
from sanic.helpers import Default, _default
from sanic.log import logger

from sanic_ext.config import Config, add_fallback_config
from sanic_ext.extensions.base import Extension
from sanic_ext.extensions.health.extension import HealthExtension
from sanic_ext.extensions.http.extension import HTTPExtension
from sanic_ext.extensions.injection.extension import InjectionExtension
from sanic_ext.extensions.injection.registry import (
    ConstantRegistry,
    InjectionRegistry,
)
from sanic_ext.extensions.logging.extension import LoggingExtension
from sanic_ext.extensions.openapi.builders import SpecificationBuilder
from sanic_ext.extensions.openapi.extension import OpenAPIExtension
from sanic_ext.utils.string import camel_to_snake
from sanic_ext.utils.version import get_version


try:
    from jinja2 import Environment

    from sanic_ext.extensions.templating.engine import Templating
    from sanic_ext.extensions.templating.extension import TemplatingExtension

    TEMPLATING_ENABLED = True
except (ImportError, ModuleNotFoundError):
    TEMPLATING_ENABLED = False

MIN_SUPPORT = (21, 3, 2)


class Extend:
    _pre_registry: List[Union[Type[Extension], Extension]] = []

    if TEMPLATING_ENABLED:
        environment: Environment
        templating: Templating

    def __init__(
        self,
        app: Sanic,
        *,
        extensions: Optional[List[Union[Type[Extension], Extension]]] = None,
        built_in_extensions: bool = True,
        config: Optional[Union[Config, Dict[str, Any]]] = None,
        **kwargs,
    ) -> None:
        """
        Ingress for instantiating sanic-ext

        :param app: Sanic application
        :type app: Sanic
        """
        if not isinstance(app, Sanic):
            raise SanicException(
                f"Cannot apply SanicExt to {app.__class__.__name__}"
            )

        sanic_version = get_version(__version__)

        if MIN_SUPPORT > sanic_version:
            min_version = ".".join(map(str, MIN_SUPPORT))
            raise SanicException(
                f"Sanic Extensions only works with Sanic v{min_version} "
                f"and above. It looks like you are running {__version__}."
            )

        self._injection_registry: Optional[InjectionRegistry] = None
        self._constant_registry: Optional[ConstantRegistry] = None
        self._openapi: Optional[SpecificationBuilder] = None
        self.app = app
        self.extensions: List[Extension] = []
        self.sanic_version = sanic_version
        app._ext = self
        app.ctx._dependencies = SimpleNamespace()

        if not isinstance(config, Config):
            config = Config.from_dict(config or {})
        self.config = add_fallback_config(app, config, **kwargs)

        extensions = extensions or []
        if built_in_extensions:
            extensions.extend(
                [
                    InjectionExtension,
                    OpenAPIExtension,
                    HTTPExtension,
                    HealthExtension,
                    LoggingExtension,
                ]
            )

            if TEMPLATING_ENABLED:
                extensions.append(TemplatingExtension)
        extensions.extend(Extend._pre_registry)

        started = set()
        for ext in extensions:
            if ext in started:
                continue
            extension = Extension.create(ext, app, self.config)
            extension._startup(self)
            self.extensions.append(extension)
            started.add(ext)

    def _display(self):
        if "SANIC_WORKER_IDENTIFIER" in os.environ:
            return
        init_logs = ["Sanic Extensions:"]
        for extension in self.extensions:
            label = extension.render_label()
            if extension.included():
                init_logs.append(f"  > {extension.name} {label}")

        list(map(logger.info, init_logs))

    def injection(
        self,
        type: Type,
        constructor: Optional[Callable[..., Any]] = None,
    ) -> None:
        warn(
            "The 'ext.injection' method has been deprecated and will be "
            "removed in v22.6. Please use 'ext.add_dependency' instead.",
            DeprecationWarning,
        )
        self.add_dependency(type=type, constructor=constructor)

    def add_dependency(
        self,
        type: Type,
        constructor: Optional[Callable[..., Any]] = None,
        request_arg: Optional[str] = None,
    ) -> None:
        """
        Add a dependency for injection

        :param type: The type of the dependency
        :type type: Type
        :param constructor: A callable that will return an instance to be
            injected, when ``False`` it will call the type, defaults to None
        :type constructor: Optional[Callable[..., Any]], optional
        :param request_arg: Explicitly state which argument in the
            constructor (if any) should be a ``Request`` object, when set to
            ``None`` the constructor will be introspected to check the
            type annotations looking for a request object. You should really
            only use this if you **MUST** use a lambda explression, it is
            otherwise better to use a properly type annotated constructor,
            defaults to None
        :type request_arg: Optional[str], optional
        :raises SanicException: _description_
        """
        if not self._injection_registry:
            raise SanicException("Injection extension not enabled")
        self._injection_registry.register(
            type, constructor, request_arg=request_arg
        )

    def add_constant(self, name: str, value: Any, overwrite: bool = False):
        if not self._constant_registry:
            raise ValueError("Cannot add constant. No registry created.")
        self._constant_registry.register(name, value, overwrite)

    def load_constants(
        self,
        constants: Optional[Mapping[str, Any]] = None,
        overwrite: Union[Default, bool] = _default,
    ):
        if not constants:
            constants = {
                k: v
                for k, v in self.app.config.items()
                if k.isupper()
                and k not in DEFAULT_CONFIG
                and k not in self.config
                and not k.startswith("_")
            }
            if isinstance(overwrite, Default):
                overwrite = True
        if isinstance(overwrite, Default):
            overwrite = False
        for name, value in constants.items():
            self.add_constant(name, value, overwrite)

    def dependency(self, obj: Any, name: Optional[str] = None) -> None:
        if not name:
            name = camel_to_snake(obj.__class__.__name__)
        setattr(self.app.ctx._dependencies, name, obj)

        def getter(*_):
            return obj

        self.add_dependency(obj.__class__, getter)

    @property
    def openapi(self) -> SpecificationBuilder:
        if not self._openapi:
            self._openapi = SpecificationBuilder()

        return self._openapi

    def template(self, template_name: str, **kwargs):
        return self.templating.template(template_name, **kwargs)

    @classmethod
    def register(cls, extension: Union[Type[Extension], Extension]) -> None:
        cls._pre_registry.append(extension)

    @classmethod
    def reset(cls) -> None:
        cls._pre_registry.clear()
