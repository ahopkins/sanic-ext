from __future__ import annotations

from dataclasses import is_dataclass
from inspect import isclass, iscoroutine
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Set,
    Tuple,
    Type,
    get_args,
    get_origin,
    get_type_hints,
)

from sanic import Request
from sanic.app import Sanic
from sanic.exceptions import ServerError

from sanic_ext.exceptions import InitError
from sanic_ext.utils.typing import (
    is_attrs,
    is_msgspec,
    is_optional,
    is_pydantic,
)


if TYPE_CHECKING:
    from .registry import ConstantRegistry, InjectionRegistry


class Constructor:
    EXEMPT_ANNOTATIONS = (Request,)

    def __init__(
        self, func: Callable[..., Any], request_arg: Optional[str] = None
    ):
        self.func = func
        self.injections: Dict[str, Tuple[Type, Constructor]] = {}
        self.constants: Dict[str, Any] = {}
        self.pass_kwargs: bool = False
        self.request_arg = request_arg

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}:{self.func.__name__}>"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(func={self.func.__name__})>"

    async def __call__(self, request, **kwargs):
        try:
            args = await gather_args(self.injections, request, **kwargs)
            args.update(self.constants)
            if self.pass_kwargs:
                args.update(kwargs)

            if self.request_arg:
                args[self.request_arg] = request

            retval = self.func(**args)

            if iscoroutine(retval):
                retval = await retval
            return retval
        except TypeError as e:
            raise ServerError(
                "Failure to inject dependencies. Make sure that all "
                f"dependencies for '{self.func.__name__}' have been "
                "registered."
            ) from e

    def prepare(
        self,
        app: Sanic,
        injection_registry: InjectionRegistry,
        constant_registry: ConstantRegistry,
        allowed_types: Set[Type[object]],
    ) -> None:
        hints = self._get_hints()
        hints.pop("return", None)
        missing = []
        for param, annotation in hints.items():
            if param in constant_registry:
                self.constants[param] = getattr(app.config, param.upper())
            if annotation in allowed_types:
                self.pass_kwargs = True
            if is_optional(annotation):
                annotation = get_args(annotation)[0]
            if not isclass(annotation) and get_origin(annotation) is None:
                missing.append((param, annotation))
                continue
            if issubclass(annotation, Request):
                self.request_arg = param
            if (
                annotation not in self.EXEMPT_ANNOTATIONS
                and not issubclass(annotation, self.EXEMPT_ANNOTATIONS)
                and annotation not in allowed_types
            ):
                dependency = injection_registry.get(annotation)
                if not dependency:
                    missing.append((param, annotation))
                    continue
                self.injections[param] = (annotation, dependency)

        if missing:
            dependencies = "\n".join(
                [f"  - {param}: {annotation}" for param, annotation in missing]
            )
            raise InitError(
                "Unable to resolve dependencies for "
                f"'{self.func.__name__}'. Could not find the following "
                f"dependencies:\n{dependencies}.\nMake sure the dependencies "
                "are declared using ext.injection. See "
                "https://sanicframework.org/en/plugins/sanic-ext/injection."
                "html#injecting-services for more details."
            )

        checked: Set[Type[object]] = set()
        current: Set[Type[object]] = set()
        self.check_circular(checked, current)

    def check_circular(
        self,
        checked: Set[Type[object]],
        current: Set[Type[object]],
    ) -> None:
        dependencies = set(self.injections.values())
        for dependency, constructor in dependencies:
            self._visit(dependency, constructor, checked, current)

    def _visit(
        self,
        dependency: Type[object],
        constructor: Constructor,
        checked: Set[Type[object]],
        current: Set[Type[object]],
    ):
        if dependency in checked:
            return
        elif dependency in current:
            raise InitError(
                "Circular dependency injection detected on "
                f"'{self.func.__name__}'. Check dependencies of "
                f"'{constructor.func.__name__}' which may contain "
                f"circular dependency chain with {dependency}."
            )

        current.add(dependency)
        constructor.check_circular(checked, current)
        current.remove(dependency)
        checked.add(dependency)

    def _get_hints(self):
        if (
            not isclass(self.func)
            or is_dataclass(self.func)
            or is_attrs(self.func)
            or is_pydantic(self.func)
            or is_msgspec(self.func)
        ):
            return get_type_hints(self.func)
        elif isclass(self.func):
            return get_type_hints(self.func.__init__)
        raise InitError(f"Cannot get type hints for {self.func}")


async def gather_args(injections, request, **kwargs) -> Dict[str, Any]:
    return {
        name: await do_cast(_type, constructor, request, **kwargs)
        for name, (_type, constructor) in injections.items()
    }


async def do_cast(_type, constructor, request, **kwargs):
    cast = constructor if constructor else _type
    args = [request] if constructor else []

    retval = cast(*args, **kwargs)
    if iscoroutine(retval):
        retval = await retval
    return retval
