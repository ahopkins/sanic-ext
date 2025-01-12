from __future__ import annotations

import os

from typing import Any, Dict, List, Optional, Sequence, Union

from sanic import Sanic
from sanic.config import Config as SanicConfig
from sanic.exceptions import SanicException
from sanic.signals import Event


PRIORITY = -1_000


class Config(SanicConfig):
    def __init__(
        self,
        cors: bool = True,
        cors_allow_headers: str = "*",
        cors_always_send: bool = True,
        cors_automatic_options: bool = True,
        cors_expose_headers: str = "",
        cors_max_age: int = 5,
        cors_methods: str = "",
        cors_origins: Union[str, List[str]] = "",
        cors_send_wildcard: bool = False,
        cors_supports_credentials: bool = False,
        cors_vary_header: bool = True,
        health: bool = False,
        health_endpoint: bool = False,
        health_max_misses: int = 3,
        health_missed_threshhold: int = 10,
        health_monitor: bool = True,
        health_report_interval: int = 5,
        health_uri_to_info: str = "",
        health_url_prefix: str = "/__health__",
        http_all_methods: bool = True,
        http_auto_head: bool = True,
        http_auto_options: bool = True,
        http_auto_trace: bool = False,
        injection_signal: Union[str, Event] = Event.HTTP_ROUTING_AFTER,
        injection_priority: int = PRIORITY,
        injection_load_custom_constants: bool = False,
        logging: bool = False,
        logging_queue_max_size: int = 4096,
        loggers: List[str] = [
            "sanic.access",
            "sanic.error",
            "sanic.root",
            "sanic.server",
            "sanic.websockets",
        ],
        oas: bool = True,
        oas_autodoc: bool = True,
        oas_custom_file: Optional[os.PathLike] = None,
        oas_ignore_head: bool = True,
        oas_ignore_options: bool = True,
        oas_path_to_redoc_html: Optional[str] = None,
        oas_path_to_swagger_html: Optional[str] = None,
        oas_ui_default: Optional[str] = "redoc",
        oas_ui_redoc: bool = True,
        oas_ui_redoc_html_title: str = "ReDoc",
        oas_ui_redoc_custom_css: str = "",
        oas_ui_swagger: bool = True,
        oas_ui_swagger_html_title: str = "OpenAPI Swagger",
        oas_ui_swagger_custom_css: str = "",
        oas_ui_swagger_version: str = "4.10.3",
        oas_ui_swagger_oauth2_redirect: str = "/oauth2-redirect.html",
        oas_uri_to_config: str = "/swagger-config",
        oas_uri_to_json: str = "/openapi.json",
        oas_uri_to_redoc: str = "/redoc",
        oas_uri_to_swagger: str = "/swagger",
        oas_url_prefix: str = "/docs",
        swagger_ui_configuration: Optional[Dict[str, Any]] = None,
        templating_path_to_templates: Union[
            str, os.PathLike, Sequence[Union[str, os.PathLike]]
        ] = "templates",
        templating_enable_async: bool = True,
        trace_excluded_headers: Sequence[str] = ("authorization", "cookie"),
        **kwargs,
    ):
        self.CORS = cors
        self.CORS_ALLOW_HEADERS = cors_allow_headers
        self.CORS_ALWAYS_SEND = cors_always_send
        self.CORS_AUTOMATIC_OPTIONS = cors_automatic_options
        self.CORS_EXPOSE_HEADERS = cors_expose_headers
        self.CORS_MAX_AGE = cors_max_age
        self.CORS_METHODS = cors_methods
        self.CORS_ORIGINS = cors_origins
        self.CORS_SEND_WILDCARD = cors_send_wildcard
        self.CORS_SUPPORTS_CREDENTIALS = cors_supports_credentials
        self.CORS_VARY_HEADER = cors_vary_header
        self.HEALTH = health
        self.HEALTH_ENDPOINT = health_endpoint
        self.HEALTH_MAX_MISSES = health_max_misses
        self.HEALTH_MISSED_THRESHHOLD = health_missed_threshhold
        self.HEALTH_MONITOR = health_monitor
        self.HEALTH_REPORT_INTERVAL = health_report_interval
        self.HEALTH_URI_TO_INFO = health_uri_to_info
        self.HEALTH_URL_PREFIX = health_url_prefix
        self.HTTP_ALL_METHODS = http_all_methods
        self.HTTP_AUTO_HEAD = http_auto_head
        self.HTTP_AUTO_OPTIONS = http_auto_options
        self.HTTP_AUTO_TRACE = http_auto_trace
        self.INJECTION_SIGNAL = injection_signal
        self.INJECTION_PRIORITY = injection_priority
        self.INJECTION_LOAD_CUSTOM_CONSTANTS = injection_load_custom_constants
        self.LOGGING = logging
        self.LOGGING_QUEUE_MAX_SIZE = logging_queue_max_size
        self.LOGGERS = loggers
        self.OAS = oas
        self.OAS_AUTODOC = oas_autodoc
        self.OAS_CUSTOM_FILE = oas_custom_file
        self.OAS_IGNORE_HEAD = oas_ignore_head
        self.OAS_IGNORE_OPTIONS = oas_ignore_options
        self.OAS_PATH_TO_REDOC_HTML = oas_path_to_redoc_html
        self.OAS_PATH_TO_SWAGGER_HTML = oas_path_to_swagger_html
        self.OAS_UI_DEFAULT = oas_ui_default
        self.OAS_UI_REDOC = oas_ui_redoc
        self.OAS_UI_REDOC_HTML_TITLE = oas_ui_redoc_html_title
        self.OAS_UI_REDOC_CUSTOM_CSS = oas_ui_redoc_custom_css
        self.OAS_UI_SWAGGER = oas_ui_swagger
        self.OAS_UI_SWAGGER_HTML_TITLE = oas_ui_swagger_html_title
        self.OAS_UI_SWAGGER_CUSTOM_CSS = oas_ui_swagger_custom_css
        self.OAS_UI_SWAGGER_VERSION = oas_ui_swagger_version
        self.OAS_UI_SWAGGER_OAUTH2_REDIRECT = oas_ui_swagger_oauth2_redirect
        self.OAS_URI_TO_CONFIG = oas_uri_to_config
        self.OAS_URI_TO_JSON = oas_uri_to_json
        self.OAS_URI_TO_REDOC = oas_uri_to_redoc
        self.OAS_URI_TO_SWAGGER = oas_uri_to_swagger
        self.OAS_URL_PREFIX = oas_url_prefix
        self.SWAGGER_UI_CONFIGURATION = swagger_ui_configuration or {
            "apisSorter": "alpha",
            "operationsSorter": "alpha",
            "docExpansion": "full",
        }
        self.TEMPLATING_PATH_TO_TEMPLATES = templating_path_to_templates
        self.TEMPLATING_ENABLE_ASYNC = templating_enable_async
        self.TRACE_EXCLUDED_HEADERS = trace_excluded_headers

        if isinstance(self.TRACE_EXCLUDED_HEADERS, str):
            self.TRACE_EXCLUDED_HEADERS = tuple(
                self.TRACE_EXCLUDED_HEADERS.split(",")
            )

        if isinstance(self.INJECTION_SIGNAL, str):
            self.INJECTION_SIGNAL = Event(self.INJECTION_SIGNAL)

        valid_signals = ("http.handler.before", "http.routing.after")
        if self.INJECTION_SIGNAL.value not in valid_signals:
            raise SanicException(
                f"Injection signal may only be one of {valid_signals}"
            )

        self.load({key.upper(): value for key, value in kwargs.items()})

    @classmethod
    def from_dict(cls, mapping) -> Config:
        return cls(**mapping)


def add_fallback_config(
    app: Sanic, config: Optional[Config] = None, **kwargs
) -> Config:
    if config is None:
        config = Config(**kwargs)

    app.config.update(
        {key: value for key, value in config.items() if key not in app.config}
    )
    config.update(
        {
            key: value
            for key, value in app.config.items()
            if key in config and value != config.get(key)
        }
    )

    return config
