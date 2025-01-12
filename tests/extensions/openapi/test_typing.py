import sys
from typing import List, Optional

import pytest

from sanic_ext.utils.typing import contains_annotations, flat_values


class Foo: ...


def test_dict_values_nested():
    values = flat_values(
        {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {"item": 999, "items": [888, 777]},
                        "item": 666,
                    },
                    "item": True,
                },
                "multiple": [
                    {"nested": {"object": None}},
                    {"nested": {"object": None}},
                ],
            },
            "item": True,
        }
    )
    assert values == {999, 888, 777, 666, None, True}


params = [
    ({"foo": str}, True),
    ({"foo": List[str]}, True),
    ({"foo": Optional[str]}, True),
    ({"foo": Foo}, True),
    ({"foo": "str"}, False),
]
if sys.version_info >= (3, 9):
    params.append(({"foo": list[str]}, True))
if sys.version_info >= (3, 10):
    params.append(({"foo": str | None}, True))


@pytest.mark.parametrize("item,expected", params)
def test_contains_annotations(item, expected):
    assert contains_annotations(item) == expected
