import pytest
from sanic import Sanic
from sanic.response import empty

from sanic_ext.extensions.logging.logger import Logger


def test_defult_config(app: Sanic):
    assert hasattr(app.config, "LOGGERS")


def test_custom_background_logger(app: Sanic):
    assert Logger.LOGGERS == []
    Logger.prepare(app)
    assert hasattr(app.shared_ctx, "logger_queue")
    assert Logger.LOGGERS == app.config.LOGGERS
    assert "sanic.root" in Logger.LOGGERS

    logger = Logger()
    assert len(logger.loggers) == len(Logger.LOGGERS) == len(app.config.LOGGERS)
