from dataclasses import asdict, dataclass

from sanic import Sanic, json

from sanic_ext.extras.validation.decorator import validate


@dataclass
class ModelA:
    a: str


@dataclass
class ModelB:
    b: str


def test_both_body_and_query(app: Sanic):
    @app.post("")
    @validate(json=ModelA, query=ModelB)
    async def test(_, body: ModelA, query: ModelB):
        return json(
            {
                "body": asdict(body),
                "query": asdict(query),
            }
        )

    _, response = app.test_client.post("")
    assert response.status == 400

    _, response = app.test_client.post("", params={"b": "bbb"})
    assert response.status == 400

    _, response = app.test_client.post("", params={"b": "bbb"}, json={"a": "aaa"})
    assert response.status == 200
    assert response.json == {
        "body": {"a": "aaa"},
        "query": {"b": "bbb"},
    }
