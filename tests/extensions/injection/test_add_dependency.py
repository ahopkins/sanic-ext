from __future__ import annotations

import asyncio
from dataclasses import dataclass
from itertools import count
from typing import Optional
from uuid import UUID

import pytest
from sanic import Request, json, text
from sanic.exceptions import SanicException
from sanic.views import HTTPMethodView

from sanic_ext import Extend


@dataclass
class Name:
    name: str


@dataclass
class PersonID:
    person_id: int


@dataclass
class NamedPerson:
    name: str


@dataclass
class Person:
    person_id: PersonID
    name: str
    age: int

    @classmethod
    async def create(cls, person_id: int) -> Person:
        return cls(person_id=PersonID(person_id), name="noname", age=111)


@dataclass
class AsyncName:
    name: str

    def __await__(self):
        return self


counter = count()


class A:
    @classmethod
    def create(cls, request: Request):
        next(counter)
        return cls()


class B:
    def __init__(self, a: A):
        self.a = a

    @classmethod
    def create(cls, request: Request, a: A):
        next(counter)
        return cls(a)


class C:
    def __init__(self, b: B):
        self.b = b

    @classmethod
    def create(cls, request: Request, b: B):
        next(counter)
        return cls(b)


class D:
    def __init__(self, a: A):
        self.a = a

    @classmethod
    def create(cls, request: Request, a: A):
        next(counter)
        return cls(a)


class E:
    def __init__(self, c: C, d: D):
        self.c = c
        self.d = d

    @classmethod
    def create(cls, request: Request, c: C, d: D):
        next(counter)
        return cls(c, d)


class Alpha: ...


class Beta:
    def __init__(self, alpha: Alpha) -> None:
        self.alpha = alpha


class Gamma:
    def __init__(self, beta: Beta, request: Optional[Request] = None) -> None:
        self.beta = beta
        self.request = request


class Delta:
    def __init__(self, gamma: Gamma, request: Request) -> None:
        self.gamma = gamma
        self.request = request


@dataclass
class Foo:
    ident: UUID


def make_gamma_with_request(beta: Beta, request: Request):
    return Gamma(beta, request)


def make_gamma_without_request(beta: Beta):
    return Gamma(beta)


def test_injection_not_allowed_when_ext_disabled(bare_app):
    ext = Extend(bare_app, built_in_extensions=False)

    with pytest.raises(SanicException, match="Injection extension not enabled"):
        ext.add_dependency(1, 2)


def test_injection_of_matched_object(app):
    @app.get("/person/<name:str>")
    def handler(request, name: Name):
        request.ctx.name = name
        return text(name.name)

    app.ext.add_dependency(Name)

    request, response = app.test_client.get("/person/george")

    assert response.body == b"george"
    assert isinstance(request.ctx.name, Name)
    assert request.ctx.name.name == "george"


def test_injection_of_matched_object_as_deprecated_injection(app):
    @app.get("/person/<name:str>")
    def handler(request, name: Name):
        request.ctx.name = name
        return text(name.name)

    message = (
        "The 'ext.injection' method has been deprecated and will be removed "
        "in v22.6. Please use 'ext.add_dependency' instead."
    )
    with pytest.warns(DeprecationWarning, match=message):
        app.ext.injection(Name)

    request, response = app.test_client.get("/person/george")

    assert response.body == b"george"
    assert isinstance(request.ctx.name, Name)
    assert request.ctx.name.name == "george"


def test_injection_of_simple_object(app):
    @app.get("/person/<name>")
    def handler(request, name: str, person: NamedPerson):
        request.ctx.person = person
        return text(person.name)

    app.ext.add_dependency(NamedPerson)

    request, response = app.test_client.get("/person/george")

    assert response.body == b"george"
    assert isinstance(request.ctx.person, NamedPerson)
    assert request.ctx.person.name == "george"


def test_injection_of_object_with_constructor(app):
    @app.get("/person/<person_id:int>")
    async def person_details(request, person_id: PersonID, person: Person):
        request.ctx.person_id = person_id
        request.ctx.person = person
        return text(f"{person.person_id.person_id}\n{person.name}\n{person.age}")

    app.ext.add_dependency(Person, Person.create)
    app.ext.add_dependency(PersonID)

    request, response = app.test_client.get("/person/999")

    assert response.body == b"999\nnoname\n111"
    assert isinstance(request.ctx.person_id, PersonID)
    assert isinstance(request.ctx.person, Person)
    assert request.ctx.person.person_id == request.ctx.person_id
    assert request.ctx.person.person_id.person_id == 999
    assert request.ctx.person.name == "noname"
    assert request.ctx.person.age == 111


def test_injection_on_cbv(app):
    class View(HTTPMethodView, attach=app, uri="/person/<name:str>"):
        async def get(self, request, name: Name):
            request.ctx.name = name
            return text(name.name)

        @staticmethod
        async def post(request, name: Name):
            request.ctx.name = name
            return text(name.name)

    app.ext.add_dependency(Name)

    for client in (app.test_client.get, app.test_client.post):
        request, response = client("/person/george")

        assert response.body == b"george"
        assert isinstance(request.ctx.name, Name)
        assert request.ctx.name.name == "george"


def test_nested_dependencies(app):
    app.ext.add_dependency(A, A.create)
    app.ext.add_dependency(B, B.create)
    app.ext.add_dependency(C, C.create)
    app.ext.add_dependency(D, D.create)
    app.ext.add_dependency(E, E.create)

    @app.get("/")
    async def nested(request: Request, c: C, e: E):
        return json(
            [
                isinstance(c, C),
                isinstance(c.b, B),
                isinstance(c.b.a, A),
                isinstance(e, E),
                isinstance(e.c, C),
                isinstance(e.d, D),
                isinstance(e.d.a, A),
            ]
        )

    _, response = app.test_client.get("/")

    assert all(response.json)
    # TODO:
    # - After implementing https://github.com/sanic-org/sanic-ext/issues/77
    #   this should be == 5
    assert next(counter) == 9


def test_injection_on_websocket(app):
    ev = asyncio.Event()

    app.ext.dependency(A())

    @app.websocket("/foo")
    async def handler(request, ws, foo: A):
        assert isinstance(foo, A)
        if isinstance(foo, A):
            ev.set()

    request, response = app.test_client.websocket("/foo")
    assert ev.is_set()


def test_injection_of_awaitable_variable_in_do_cast(app):
    """Test for do_cast() iscoroutine() check"""

    @app.get("/person/<name:str>")
    def handler(request, name: AsyncName):
        request.ctx.name = name
        return text(name.name)

    app.ext.add_dependency(AsyncName)

    request, response = app.test_client.get("/person/george")

    assert response.body == b"george"
    assert isinstance(request.ctx.name, AsyncName)
    assert request.ctx.name.name == "george"


def test_injection_of_awaitable_variable_in_call(app):
    """Test for __call__() iscoroutine() check"""

    @app.get("/person/<name:str>")
    def handler(request, name: AsyncName):
        request.ctx.name = name
        return text(name.name)

    def test():
        return AsyncName("george")

    app.ext.dependency(test())

    request, response = app.test_client.get("/person/george")

    assert response.body == b"george"
    assert isinstance(request.ctx.name, AsyncName)
    assert request.ctx.name.name == "george"


def test_injection_class_constructors(app):
    app.ext.add_dependency(Alpha)
    app.ext.add_dependency(Beta)

    @app.get("/")
    def handler(request: Request, beta: Beta):
        return json({"is_beta": isinstance(beta, Beta)})

    _, response = app.test_client.get("/")
    assert response.json == {"is_beta": True}


def test_injection_class_constructors_with_optional_request(app):
    app.ext.add_dependency(Alpha)
    app.ext.add_dependency(Beta)
    app.ext.add_dependency(Gamma)

    @app.get("/")
    def handler(request: Request, gamma: Gamma):
        return json(
            {
                "is_gamma": isinstance(gamma, Gamma),
                "has_request": bool(gamma.request),
            }
        )

    _, response = app.test_client.get("/")
    assert response.json == {"is_gamma": True, "has_request": True}


def test_injection_class_constructors_with_request(app):
    app.ext.add_dependency(Alpha)
    app.ext.add_dependency(Beta)
    app.ext.add_dependency(Gamma)
    app.ext.add_dependency(Delta)

    @app.get("/")
    def handler(request: Request, delta: Delta):
        return json(
            {
                "is_delta": isinstance(delta, Delta),
                "has_request": bool(delta.request),
            }
        )

    _, response = app.test_client.get("/")
    assert response.json == {"is_delta": True, "has_request": True}


def test_injection_class_constructors_with_func_and_request(app):
    app.ext.add_dependency(Alpha)
    app.ext.add_dependency(Beta)
    app.ext.add_dependency(Gamma, make_gamma_with_request)

    @app.get("/")
    def handler(request: Request, gamma: Gamma):
        return json(
            {
                "is_gamma": isinstance(gamma, Gamma),
                "has_request": bool(gamma.request),
            }
        )

    _, response = app.test_client.get("/")
    assert response.json == {"is_gamma": True, "has_request": True}


def test_injection_class_constructors_with_func_and_no_request(app):
    app.ext.add_dependency(Alpha)
    app.ext.add_dependency(Beta)
    app.ext.add_dependency(Gamma, make_gamma_without_request)

    @app.get("/")
    def handler(request: Request, gamma: Gamma):
        return json(
            {
                "is_gamma": isinstance(gamma, Gamma),
                "has_request": bool(gamma.request),
            }
        )

    _, response = app.test_client.get("/")
    assert response.json == {"is_gamma": True, "has_request": False}


def test_injection_of_lambda_properties(app):
    @app.get("/foo")
    def handler(request, foo: Foo):
        return json(request.id == foo.ident and isinstance(foo.ident, UUID))

    app.ext.add_dependency(Foo, lambda request: Foo(request.id), "request")

    _, response = app.test_client.get("/foo")

    assert response.body == b"true"
