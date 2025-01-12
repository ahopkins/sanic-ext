import sys
from dataclasses import dataclass
from typing import List, Optional

import pytest
from sanic import json
from sanic.views import HTTPMethodView

from sanic_ext import validate
from sanic_ext.extras.validation.check import check_data
from sanic_ext.extras.validation.schema import make_schema, parse_hint

from . import __models__ as models

SNOOPY_DATA = {"name": "Snoopy", "alter_ego": ["Flying Ace", "Joe Cool"]}


def test_schema():
    @dataclass
    class Pet:
        name: str

    @dataclass
    class Person:
        name: str
        age: int
        pets: Optional[List[Pet]]

    schema = make_schema({}, Person)

    assert "Person" in schema
    assert schema["Person"]["hints"]["name"] == parse_hint(str)
    assert schema["Person"]["hints"]["age"] == parse_hint(int)
    assert schema["Person"]["hints"]["pets"] == parse_hint(Optional[List[Pet]])

    assert "Pet" in schema
    assert schema["Pet"]["hints"]["name"] == parse_hint(str)


def test_should_hydrate():
    @dataclass
    class Pet:
        name: str

    @dataclass
    class Person:
        name: str
        age: int
        pets: List[Pet]

    data = {"name": "Charlie Brown", "age": 8, "pets": [{"name": "Snoopy"}]}

    schema = make_schema({}, Person)
    cb = check_data(Person, data, schema)

    assert cb.name == "Charlie Brown"
    assert cb.age == 8
    assert cb.pets[0].name == "Snoopy"


@pytest.mark.parametrize(
    "data",
    (
        {"name": "Charlie Brown", "age": 8, "pets": {"name": "Snoopy"}},
        {"name": "Charlie Brown", "age": 8, "pets": [{"name": 123}]},
        {"name": "Charlie Brown", "age": 8, "pets": [123]},
        {"name": "Charlie Brown", "age": 8, "pets": 123},
        {"name": "Charlie Brown", "age": "8", "pets": {"name": "Snoopy"}},
        {"name": True, "age": 8, "pets": {"name": "Snoopy"}},
    ),
)
def test_should_not_hydrate(data):
    @dataclass
    class Pet:
        name: str

    @dataclass
    class Person:
        name: str
        age: int
        pets: List[Pet]

    schema = make_schema({}, Person)
    with pytest.raises(TypeError):
        check_data(Person, data, schema)


@pytest.mark.parametrize(
    "model,okay,data",
    (
        (models.ModelStr, True, {"foo": "bar"}),
        (models.ModelStr, False, {"foo": 1}),
        (models.ModelStr, False, {"foo": True}),
        (models.ModelStr, False, {"foo": ["bar"]}),
        (models.ModelStr, False, {"bar": "bar"}),
        (models.ModelStr, False, {"foo": None}),
        (models.ModelStr, False, 123),
        (models.ModelInt, True, {"foo": 1}),
        (models.ModelInt, True, {"foo": True}),
        (models.ModelInt, False, {"foo": "1"}),
        (models.ModelInt, False, {"foo": 1.1}),
        (models.ModelInt, False, {"foo": None}),
        (models.ModelFloat, True, {"foo": 1.1}),
        (models.ModelFloat, False, {"foo": 1}),
        (models.ModelFloat, False, {"foo": "1.1"}),
        (models.ModelFloat, False, {"foo": None}),
        (models.ModelBool, True, {"foo": True}),
        (models.ModelBool, True, {"foo": False}),
        (models.ModelBool, False, {"foo": 1}),
        (models.ModelBool, False, {"foo": 0}),
        (models.ModelBool, False, {"foo": 2}),
        (models.ModelBool, False, {"foo": "True"}),
        (models.ModelBool, False, {"foo": None}),
        (models.ModelOptionalStr, True, {"foo": "bar"}),
        (models.ModelOptionalStr, True, {"foo": None}),
        (models.ModelOptionalStr, False, {"foo": 0}),
        (models.ModelUnion, True, {"foo": 1}),
        (models.ModelUnion, True, {"foo": 1.1}),
        (models.ModelUnion, False, {"foo": "1.1"}),
        (models.ModelUnion, False, {"foo": None}),
        (models.ModelUnionModels, True, {"foo": {"foo": 1}}),
        (models.ModelUnionModels, True, {"foo": {"foo": 1.1}}),
        (models.ModelUnionModels, False, {"foo": {"foo": "1.1"}}),
        (models.ModelUnionModels, False, {"foo": 1}),
        (models.ModelUnionModels, False, {"foo": 1.1}),
        (models.ModelUnionModels, False, {"foo": None}),
        (models.ModelUnionStrInt, True, {"foo": "1"}),
        (models.ModelUnionStrInt, True, {"foo": "1q"}),
        (models.ModelUnionStrInt, True, {"foo": 1}),
        (models.ModelUnionStrInt, False, {"foo": 1.1}),
        (models.ModelUnionStrInt, False, {"foo": None}),
        (models.ModelUnionIntStr, True, {"foo": "1"}),
        (models.ModelUnionIntStr, True, {"foo": "1q"}),
        (models.ModelUnionIntStr, True, {"foo": 1}),
        (models.ModelUnionIntStr, False, {"foo": 1.1}),
        (models.ModelUnionIntStr, False, {"foo": None}),
        (models.ModelOptionalUnionStrInt, True, {"foo": "1"}),
        (models.ModelOptionalUnionStrInt, True, {"foo": "1q"}),
        (models.ModelOptionalUnionStrInt, True, {"foo": 1}),
        (models.ModelOptionalUnionStrInt, False, {"foo": 1.1}),
        (models.ModelOptionalUnionStrInt, True, {"foo": None}),
        (models.ModelOptionalUnionIntStr, True, {"foo": "1"}),
        (models.ModelOptionalUnionIntStr, True, {"foo": "1q"}),
        (models.ModelOptionalUnionIntStr, True, {"foo": 1}),
        (models.ModelOptionalUnionIntStr, False, {"foo": 1.1}),
        (models.ModelOptionalUnionIntStr, True, {"foo": None}),
        (models.ModelListStr, True, {"foo": ["bar"]}),
        (models.ModelListStr, True, {"foo": ["one", "two"]}),
        (models.ModelListStr, False, {"foo": "bar"}),
        (models.ModelListStr, False, {"foo": ["one", 2]}),
        (models.ModelListStr, False, {"foo": ["one", None]}),
        (models.ModelListStr, False, {"foo": None}),
        (models.ModelListModel, True, {"foo": [{"foo": "bar"}]}),
        (
            models.ModelListModel,
            True,
            {"foo": [{"foo": "one"}, {"foo": "two"}]},
        ),
        (models.ModelListModel, False, {"foo": {"foo": "bar"}}),
        (models.ModelListModel, False, {"foo": [{"foo": "bar"}, 2]}),
        (models.ModelListModel, False, {"foo": [{"foo": "bar"}, None]}),
        (models.ModelListModel, False, {"foo": None}),
        (models.ModelOptionalList, True, {"foo": None}),
        (models.ModelOptionalList, True, {"foo": ["bar"]}),
        (models.ModelOptionalList, False, {"foo": [1]}),
        (models.ModelOptionalList, False, {"foo": [None]}),
        (models.ModelListUnion, True, {"foo": [1]}),
        (models.ModelListUnion, True, {"foo": [1.1]}),
        (models.ModelListUnion, True, {"foo": [1, 1.1]}),
        (models.ModelListUnion, False, {"foo": [1, 1.1, "one"]}),
        (models.ModelListUnion, False, {"foo": [1, 1.1, None]}),
        (models.ModelListUnion, False, {"foo": 1}),
        (models.ModelListUnion, False, {"foo": 1.1}),
        (models.ModelListUnion, False, {"foo": None}),
        (models.ModelOptionalListUnion, True, {"foo": [1]}),
        (models.ModelOptionalListUnion, True, {"foo": [1.1]}),
        (models.ModelOptionalListUnion, True, {"foo": [1, 1.1]}),
        (models.ModelOptionalListUnion, True, {"foo": None}),
        (models.ModelOptionalListUnion, False, {"foo": [1, 1.1, "one"]}),
        (models.ModelOptionalListUnion, False, {"foo": [1, 1.1, None]}),
        (models.ModelOptionalListUnion, False, {"foo": 1}),
        (models.ModelOptionalListUnion, False, {"foo": 1.1}),
        (models.ModelModel, True, {"foo": {"foo": "one"}}),
        (models.ModelModel, False, {"foo": {"foo": 1}}),
        (models.ModelModel, False, {"foo": {"foo": None}}),
        (models.ModelModel, False, {"foo": "one"}),
        (models.ModelModel, False, {"foo": None}),
        (models.ModelOptionalModel, True, {"foo": {"foo": "one"}}),
        (models.ModelOptionalModel, True, {"foo": None}),
        (models.ModelOptionalModel, False, {"foo": {"foo": 1}}),
        (models.ModelOptionalModel, False, {"foo": {"foo": None}}),
        (models.ModelOptionalModel, False, {"foo": "one"}),
        (models.ModelDictStr, True, {"foo": {"foo": "one"}}),
        (models.ModelDictStr, False, {"foo": {"foo": 1}}),
        (models.ModelDictStr, False, {"foo": {"foo": None}}),
        (models.ModelDictStr, False, {"foo": "one"}),
        (models.ModelDictStr, False, {"foo": None}),
        (models.ModelDictModel, True, {"foo": {"foo": {"foo": "one"}}}),
        (models.ModelDictModel, False, {"foo": {"foo": {"foo": 1}}}),
        (models.ModelDictModel, False, {"foo": {"foo": 1}}),
        (models.ModelDictModel, False, {"foo": {"foo": None}}),
        (models.ModelDictModel, False, {"foo": "one"}),
        (models.ModelDictModel, False, {"foo": None}),
        (models.ModelOptionalDict, True, {"foo": {"foo": "one"}}),
        (models.ModelOptionalDict, True, {"foo": None}),
        (models.ModelOptionalDict, False, {"foo": {"foo": 1}}),
        (models.ModelOptionalDict, False, {"foo": {"foo": None}}),
        (models.ModelOptionalDict, False, {"foo": "one"}),
        (models.ModelDictUnion, True, {"foo": {"foo": 1}}),
        (models.ModelDictUnion, True, {"foo": {"foo": 1.1}}),
        (models.ModelDictUnion, False, {"foo": {"foo": "one"}}),
        (models.ModelDictUnion, False, {"foo": {"foo": None}}),
        (models.ModelDictUnion, False, {"foo": "one"}),
        (models.ModelDictUnion, False, {"foo": 1}),
        (models.ModelDictUnion, False, {"foo": 1.1}),
        (models.ModelDictUnion, False, {"foo": None}),
        (models.ModelOptionalDictUnion, True, {"foo": {"foo": 1}}),
        (models.ModelOptionalDictUnion, True, {"foo": {"foo": 1.1}}),
        (models.ModelOptionalDictUnion, True, {"foo": None}),
        (models.ModelOptionalDictUnion, False, {"foo": {"foo": "one"}}),
        (models.ModelOptionalDictUnion, False, {"foo": {"foo": None}}),
        (models.ModelOptionalDictUnion, False, {"foo": "one"}),
        (models.ModelOptionalDictUnion, False, {"foo": 1}),
        (models.ModelOptionalDictUnion, False, {"foo": 1.1}),
        (models.ModelSingleLiteral, True, {"foo": True}),
        (models.ModelSingleLiteral, False, {"foo": False}),
        (models.ModelSingleLiteral, False, {"foo": "True"}),
        (models.ModelSingleLiteral, False, {"foo": None}),
        (models.ModelOptionalSingleLiteral, True, {"foo": True}),
        (models.ModelOptionalSingleLiteral, True, {"foo": None}),
        (models.ModelOptionalSingleLiteral, False, {"foo": False}),
        (models.ModelOptionalSingleLiteral, False, {"foo": "True"}),
        (models.ModelOptionalMultipleLiteral, True, {"foo": True}),
        (models.ModelOptionalMultipleLiteral, True, {"foo": 1}),
        (models.ModelOptionalMultipleLiteral, True, {"foo": "y"}),
        (models.ModelOptionalMultipleLiteral, True, {"foo": "Y"}),
        (models.ModelOptionalMultipleLiteral, True, {"foo": None}),
        (models.ModelOptionalMultipleLiteral, False, {"foo": "n"}),
        (models.ModelOptionalMultipleLiteral, False, {"foo": False}),
        (models.ModelListStrWithDefaultFactory, True, {}),
        (models.ModelListStrWithDefaultFactory, True, {"foo": ["bar"]}),
        (models.ModelListStrWithDefaultFactory, True, {"foo": []}),
        (models.ModelListStrWithDefaultFactory, False, {"foo": [1]}),
        (models.ModelListStrWithDefaultFactory, False, {"foo": None}),
    ),
)
def test_modeling(model, okay, data):
    schema = make_schema({}, model)

    if okay:
        check_data(model, data, schema)
    else:
        with pytest.raises(TypeError):
            check_data(model, data, schema)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="UnionType added in 3.10")
def test_modeling_union_type_ModelUnionTypeStrNone():
    schema = make_schema({}, models.ModelUnionTypeStrNone)

    check_data(models.ModelUnionTypeStrNone, {"foo": "bar"}, schema)
    check_data(models.ModelUnionTypeStrNone, {"foo": None}, schema)
    with pytest.raises(TypeError):
        check_data(models.ModelUnionTypeStrNone, {"foo": 0}, schema)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="UnionType added in 3.10")
def test_modeling_union_type_ModelUnionTypeStrIntNone():
    schema = make_schema({}, models.ModelUnionTypeStrIntNone)

    check_data(models.ModelUnionTypeStrIntNone, {"foo": "1"}, schema)
    check_data(models.ModelUnionTypeStrIntNone, {"foo": "bar"}, schema)
    check_data(models.ModelUnionTypeStrIntNone, {"foo": None}, schema)
    check_data(models.ModelUnionTypeStrIntNone, {"foo": 1}, schema)
    check_data(models.ModelUnionTypeStrIntNone, {"foo": 0}, schema)
    with pytest.raises(TypeError):
        check_data(models.ModelUnionTypeStrIntNone, {"foo": 1.1}, schema)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="UnionType added in 3.10")
def test_modeling_union_type_ModelUnionTypeStrInt():
    schema = make_schema({}, models.ModelUnionTypeStrInt)

    check_data(models.ModelUnionTypeStrInt, {"foo": "1"}, schema)
    check_data(models.ModelUnionTypeStrInt, {"foo": "bar"}, schema)
    check_data(models.ModelUnionTypeStrInt, {"foo": 1}, schema)
    check_data(models.ModelUnionTypeStrInt, {"foo": 0}, schema)
    with pytest.raises(TypeError):
        check_data(models.ModelUnionTypeStrInt, {"foo": None}, schema)
    with pytest.raises(TypeError):
        check_data(models.ModelUnionTypeStrInt, {"foo": 1.1}, schema)


def test_validate_json(app):
    @dataclass
    class Pet:
        name: str
        alter_ego: List[str]

    @app.post("/function")
    @validate(json=Pet)
    async def handler(_, body: Pet):
        return json(
            {
                "is_pet": isinstance(body, Pet),
                "pet": {"name": body.name, "alter_ego": body.alter_ego},
            }
        )

    class MethodView(HTTPMethodView, attach=app, uri="/method"):
        decorators = [validate(json=Pet)]

        async def post(self, _, body: Pet):
            return json(
                {
                    "is_pet": isinstance(body, Pet),
                    "pet": {"name": body.name, "alter_ego": body.alter_ego},
                }
            )

    _, response = app.test_client.post("/function", json=SNOOPY_DATA)
    assert response.status == 200
    assert response.json["is_pet"]
    assert response.json["pet"] == SNOOPY_DATA

    _, response = app.test_client.post("/method", json=SNOOPY_DATA)
    assert response.status == 200
    assert response.json["is_pet"]
    assert response.json["pet"] == SNOOPY_DATA


def test_validate_form(app):
    @dataclass
    class Pet:
        name: str
        alter_ego: List[str]
        description: Optional[str] = None

    @app.post("/function")
    @validate(form=Pet)
    async def handler(_, body: Pet):
        return json(
            {
                "is_pet": isinstance(body, Pet),
                "pet": {"name": body.name, "alter_ego": body.alter_ego},
                "description": body.description if body.description else "",
            }
        )

    class MethodView(HTTPMethodView, attach=app, uri="/method"):
        decorators = [validate(form=Pet)]

        async def post(self, _, body: Pet):
            return json(
                {
                    "is_pet": isinstance(body, Pet),
                    "pet": {"name": body.name, "alter_ego": body.alter_ego},
                    "description": body.description if body.description else "",
                }
            )

    _, response = app.test_client.post("/function", data=SNOOPY_DATA)
    assert response.status == 200
    assert response.json["is_pet"]
    assert response.json["pet"] == SNOOPY_DATA
    assert response.json["description"] == ""

    _, response = app.test_client.post("/method", data=SNOOPY_DATA)
    assert response.status == 200
    assert response.json["is_pet"]
    assert response.json["pet"] == SNOOPY_DATA
    assert response.json["description"] == ""


def test_validate_query(app):
    @dataclass
    class Search:
        q: str

    @app.get("/function")
    @validate(query=Search)
    async def handler(_, query: Search):
        return json({"q": query.q, "is_search": isinstance(query, Search)})

    class MethodView(HTTPMethodView, attach=app, uri="/method"):
        decorators = [validate(query=Search)]

        async def get(self, _, query: Search):
            return json({"q": query.q, "is_search": isinstance(query, Search)})

    _, response = app.test_client.get("/function", params={"q": "Snoopy"})
    assert response.status == 200
    assert response.json["is_search"]
    assert response.json["q"] == "Snoopy"

    _, response = app.test_client.get("/method", params={"q": "Snoopy"})
    assert response.status == 200
    assert response.json["is_search"]
    assert response.json["q"] == "Snoopy"
