from sys import version_info
from typing import List

import pytest

from sanic_ext.extensions.openapi.types import Schema, String


@pytest.mark.skipif(version_info < (3, 9), reason="Not needed on 3.8")
def test_schema_list():
    class Foo:
        list1: List[int]
        list2: list[int]

        @property
        def show(self) -> bool:
            return True

        def no_show_method(self) -> None: ...

        @classmethod
        def no_show_classmethod(self) -> None: ...

        @staticmethod
        def no_show_staticmethod() -> None: ...

    schema = Schema.make(Foo)
    serialized = schema.serialize()

    assert "no_show_method" not in serialized
    assert "no_show_classmethod" not in serialized
    assert "no_show_staticmethod" not in serialized
    assert serialized == {
        "type": "object",
        "properties": {
            "list1": {
                "type": "array",
                "items": {"type": "integer", "format": "int32"},
            },
            "list2": {
                "type": "array",
                "items": {"type": "integer", "format": "int32"},
            },
            "show": {"type": "boolean"},
        },
    }


def test_schema_fields():
    class Pet:
        name = String(example="Snoopy")

    class Single:
        pet = Pet

        class Ignore: ...

    class Multiple:
        pets = [Pet]

    pet_schema = Schema.make(Pet).serialize()
    single_schema = Schema.make(Single).serialize()
    multiple_schema = Schema.make(Multiple).serialize()

    assert pet_schema == {
        "type": "object",
        "properties": {"name": {"type": "string", "example": "Snoopy"}},
    }
    assert single_schema == {
        "type": "object",
        "properties": {"pet": pet_schema},
    }
    assert multiple_schema == {
        "type": "object",
        "properties": {"pets": {"type": "array", "items": pet_schema}},
    }
