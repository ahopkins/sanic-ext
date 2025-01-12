from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import attrs
import pytest
from msgspec import Struct
from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydataclass

from sanic_ext import openapi

from .utils import get_spec


@dataclass
class AlertDataclass:
    hit: Dict[str, int]
    last_updated: datetime


@dataclass
class AlertResponseDataclass:
    alert: AlertDataclass
    rule_id: str


class AlertPydanticBaseModel(BaseModel):
    hit: Dict[str, int]
    last_updated: datetime


class AlertResponsePydanticBaseModel(BaseModel):
    alert: AlertPydanticBaseModel
    rule_id: str


class AlertMsgspecBaseModel(Struct):
    hit: Dict[str, int]
    last_updated: datetime


class AlertResponseMsgspecBaseModel(Struct):
    alert: AlertMsgspecBaseModel
    rule_id: str


@pydataclass
class AlertPydanticDataclass:
    hit: Dict[str, int]
    last_updated: datetime


@pydataclass
class AlertResponsePydanticDataclass:
    alert: AlertPydanticDataclass
    rule_id: str


@attrs.define
class AlertAttrs:
    hit: Dict[str, int]
    last_updated: datetime


@attrs.define
class AlertResponseAttrs:
    alert: AlertAttrs
    rule_id: str


@pytest.mark.parametrize(
    "AlertResponse,check_alert",
    (
        (AlertResponseDataclass, False),
        (AlertResponseAttrs, False),
        (AlertResponseMsgspecBaseModel, True),
        (AlertResponsePydanticBaseModel, True),
        (AlertResponsePydanticDataclass, True),
    ),
)
def test_pydantic_base_model(app, AlertResponse, check_alert):
    @app.get("/")
    @openapi.definition(body={"application/json": openapi.Component(AlertResponse)})
    async def handler(_): ...

    spec = get_spec(app)
    alert_response_name = AlertResponse.__name__
    alert_name = "Alert" + alert_response_name[13:]

    assert spec["paths"]["/"]["get"]["requestBody"] == {
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{alert_response_name}"}
            }
        }
    }
    assert alert_response_name in spec["components"]["schemas"]

    if check_alert:
        assert alert_name in spec["components"]["schemas"]
        assert spec["components"]["schemas"][alert_response_name]["properties"][
            "alert"
        ] == {"$ref": f"#/components/schemas/{alert_name}"}
