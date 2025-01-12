import logging

from typing import Any, Dict, Optional, TypedDict


class LoggerConfig(TypedDict):
    level: str
    propagate: bool
    handlers: list[str]


class HandlerConfig(TypedDict):
    class_: str
    level: str
    stream: Optional[str]
    formatter: Optional[str]


class FormatterConfig(TypedDict):
    class_: str
    format: Optional[str]
    datefmt: Optional[str]


class LoggingConfig(TypedDict):
    version: int
    disable_existing_loggers: bool
    formatters: Dict[str, FormatterConfig]
    handlers: Dict[str, HandlerConfig]
    loggers: Dict[str, LoggerConfig]


class LoggingConfigExtractor:
    def __init__(self):
        self.version = 1
        self.disable_existing_loggers = False
        self.formatters: Dict[str, FormatterConfig] = {}
        self.handlers: Dict[str, HandlerConfig] = {}
        self.loggers: Dict[str, LoggerConfig] = {}

    def add_logger(self, logger: logging.Logger):
        self._extract_logger_config(logger)
        self._extract_handlers(logger)

    def compile(self) -> LoggingConfig:
        output = {
            "version": self.version,
            "disable_existing_loggers": self.disable_existing_loggers,
            "formatters": self.formatters,
            "handlers": self.handlers,
            "loggers": self.loggers,
        }
        return self._clean(output)

    def _extract_logger_config(self, logger: logging.Logger):
        config: LoggerConfig = {
            "level": logging.getLevelName(logger.level),
            "propagate": logger.propagate,
            "handlers": [handler.get_name() for handler in logger.handlers],
        }
        self.loggers[logger.name] = config

    def _extract_handlers(self, logger: logging.Logger):
        for handler in logger.handlers:
            self._extract_handler_config(handler)

    def _extract_handler_config(self, handler: logging.Handler):
        handler_name = handler.get_name()
        if handler_name in self.handlers:
            return
        config: HandlerConfig = {
            "class_": self._full_name(handler),
            "level": logging.getLevelName(handler.level),
            "formatter": (
                self._formatter_name(handler.formatter)
                if handler.formatter
                else None
            ),
            "stream": None,
        }
        # if (stream := getattr(handler, "stream", None)) and (
        #     stream_name := getattr(stream, "name", None)
        # ):
        #     config["stream"] = stream_name
        self.handlers[handler_name] = config
        if handler.formatter:
            self._extract_formatter_config(handler.formatter)

    def _extract_formatter_config(self, formatter: logging.Formatter):
        formatter_name = self._formatter_name(formatter)
        if formatter_name in self.formatters:
            return
        config: FormatterConfig = {
            "class_": self._full_name(formatter),
            "format": formatter._fmt,
            "datefmt": formatter.datefmt,
        }
        self.formatters[formatter_name] = config

    def _clean(self, d: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k.replace("class_", "class"): self._clean(v)
            if isinstance(v, dict)
            else v
            for k, v in d.items()
        }

    @staticmethod
    def _formatter_name(
        formatter: logging.Formatter, prefix: str = "formatter"
    ):
        return f"{prefix}_{formatter.__class__.__name__}".lower()

    @staticmethod
    def _full_name(obj):
        return f"{obj.__module__}.{obj.__class__.__name__}"
