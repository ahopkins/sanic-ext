from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call

import pytest
from sanic import Request
from sanic.exceptions import ServerError

from sanic_ext.exceptions import InitError
from sanic_ext.extensions.injection.constructor import Constructor, gather_args
from sanic_ext.extensions.injection.registry import (
    ConstantRegistry,
    InjectionRegistry,
)


class Foo:
    def __init__(self, num: int):
        self.num = num
        self.mock = AsyncMock()

    @classmethod
    async def create(cls, request: Request, bar: int):
        instance = cls(bar)
        await instance.mock(request, bar)
        return instance


class Bar:
    def __init__(self, foo: Foo):
        self.foo = foo

    @classmethod
    async def create(cls, request: Request, foo: Foo):
        return cls(foo)


class Chicken:
    @classmethod
    def create(cls, egg: Egg):
        return cls()


class Egg:
    @classmethod
    def create(cls, chicken: Chicken):
        return cls()


class InheritedRequest(Request): ...


class Baz:
    @classmethod
    async def create(cls, request: InheritedRequest):
        return cls()


@pytest.mark.asyncio
async def test_gather_args():
    func = AsyncMock()
    func.return_value = 999
    injections = {"some_foo": (Foo, func)}
    request = object()
    kwargs = {"zero": 0, "one": True, "two": "2", "three": None}

    args = await gather_args(injections, request, **kwargs)
    assert args == {"some_foo": 999}
    assert func.call_args == call(request, **kwargs)


@pytest.mark.asyncio
async def test_circular_refs():
    injections = InjectionRegistry()
    injections.register(Chicken, Chicken.create)
    injections.register(Egg, Egg.create)

    assert isinstance(injections[Chicken], Constructor)
    assert isinstance(injections[Egg], Constructor)

    message = (
        "Circular dependency injection detected on 'create'. Check "
        "dependencies of 'create' which may contain circular dependency "
        f"chain with {Chicken}."
    )
    with pytest.raises(InitError, match=message):
        injections.finalize(Mock(), ConstantRegistry({}), [])


@pytest.mark.asyncio
@pytest.mark.parametrize("raises,allowed", ((False, (int,)), (True, [])))
async def test_finalize_allowed_types(raises, allowed):
    injections = InjectionRegistry()
    injections.register(Foo, Foo.create)

    if raises:
        with pytest.raises(
            InitError, match=".Could not find the following dependencies."
        ):
            injections.finalize(Mock(), ConstantRegistry({}), allowed)
    else:
        injections.finalize(Mock(), ConstantRegistry({}), allowed)


@pytest.mark.asyncio
async def test_constructor():
    injections = InjectionRegistry()
    injections.register(Foo, Foo.create)
    injections.finalize(Mock(), ConstantRegistry({}), {int})
    request = object()
    constructor = injections[Foo]

    foo = await constructor(request, bar=999)

    assert isinstance(foo, Foo)
    assert foo.num == 999
    assert constructor.pass_kwargs
    foo.mock.assert_awaited_once_with(request, 999)


@pytest.mark.asyncio
async def test_constructor_nested():
    injections = InjectionRegistry()
    injections.register(Foo, Foo.create)
    injections.register(Bar, Bar.create)
    injections.finalize(Mock(), ConstantRegistry({}), {int})
    request = object()
    constructor_bar = injections[Bar]

    bar = await constructor_bar(request, bar=999)

    assert isinstance(bar, Bar)
    assert isinstance(bar.foo, Foo)
    assert bar.foo.num == 999
    assert not constructor_bar.pass_kwargs
    bar.foo.mock.assert_awaited_once_with(request, 999)


@pytest.mark.asyncio
async def test_constructor_failure_kwargs():
    injections = InjectionRegistry()
    injections.register(Foo, Foo.create)
    injections.finalize(Mock(), ConstantRegistry({}), {int})
    request = object()
    constructor = injections[Foo]

    message = (
        "Failure to inject dependencies. Make sure that all dependencies "
        "for 'create' have been registered."
    )
    with pytest.raises(ServerError, match=message):
        await constructor(request)


@pytest.mark.asyncio
async def test_constructor_failure_nested():
    injections = InjectionRegistry()
    injections.register(Foo, Foo.create)
    injections.register(Bar, Bar.create)
    injections.finalize(Mock(), ConstantRegistry({}), {int})
    request = object()
    constructor: Bar = injections[Bar]

    message = (
        "Failure to inject dependencies. Make sure that all dependencies "
        "for 'create' have been registered."
    )
    with pytest.raises(ServerError, match=message):
        await constructor(request)


@pytest.mark.asyncio
async def test_constructor_with_inherited_request():
    injections = InjectionRegistry()
    injections.register(Baz, Baz.create)
    injections.finalize(Mock(), ConstantRegistry({}), [])

    request = object()
    constructor_baz = injections[Baz]

    baz = await constructor_baz(request)

    assert isinstance(baz, Baz)
    assert not constructor_baz.pass_kwargs
