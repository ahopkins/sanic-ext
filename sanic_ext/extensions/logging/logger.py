import logging

from collections import defaultdict
from logging import LogRecord
from logging.handlers import QueueHandler
from multiprocessing import Manager
from queue import Empty, Full
from signal import SIGINT, SIGTERM
from signal import signal as signal_func
from typing import List

from sanic import Sanic
from sanic.log import logger as root_logger
from sanic.log import logger as server_logger
from sanic.logging.setup import setup_logging

from sanic_ext.extensions.logging.extractor import LoggingConfigExtractor


async def prepare_logger(app: Sanic, *_):
    Logger.prepare(app)


async def setup_logger(app: Sanic, *_):
    logger = Logger()
    extractor = LoggingConfigExtractor()
    for logger_name in app.config.LOGGERS:
        l = logging.getLogger(logger_name)
        extractor.add_logger(l)
    app.manager.manage(
        "Logger",
        logger,
        {
            "queue": app.shared_ctx.logger_queue,
            "config": extractor.compile(),
        },
        transient=True,
    )


class SanicQueueHandler(QueueHandler):
    def emit(self, record: LogRecord) -> None:
        try:
            return super().enqueue(record)
        except Full:
            server_logger.warning(
                "Background logger is full. Emitting log in process."
            )
            server_logger.handle(record)


async def setup_server_logging(app: Sanic):
    qhandler = SanicQueueHandler(app.shared_ctx.logger_queue)
    app.ctx._logger_handlers = defaultdict(list)
    app.ctx._qhandler = qhandler

    for logger_name in app.config.LOGGERS:
        logger_instance = logging.getLogger(logger_name)
        for handler in logger_instance.handlers:
            logger_instance.removeHandler(handler)
        logger_instance.addHandler(qhandler)


async def remove_server_logging(app: Sanic):
    for logger, handlers in app.ctx._logger_handlers.items():
        logger.removeHandler(app.ctx._qhandler)
        for handler in handlers:
            logger.addHandler(handler)


class Logger:
    LOGGERS: List[str] = []

    def __init__(self):
        self.run = True
        self.loggers = {
            logger: logging.getLogger(logger) for logger in self.LOGGERS
        }

    def __call__(self, queue, config) -> None:
        signal_func(SIGINT, self.stop)
        signal_func(SIGTERM, self.stop)

        logging.config.dictConfig(config)

        setup_loggers = set(config["loggers"].keys())
        enabled_loggers = set(self.loggers.keys())
        missing = enabled_loggers - setup_loggers
        root_logger.info(
            f"Setup background logging for: {', '.join(setup_loggers)}"
        )
        if missing:
            root_logger.warning(
                f"Logger config not found for: {', '.join(missing)}"
            )
        setup_logging(True, no_color=False, log_extra=True)

        while self.run:
            try:
                record: LogRecord = queue.get(timeout=0.05)
            except Empty:
                continue
            logger = self.loggers.get(record.name)
            logger.handle(record)

    def stop(self, *_):
        if self.run:
            self.run = False

    @classmethod
    def update_cls_loggers(cls, logger_names: List[str]):
        cls.LOGGERS = logger_names

    @classmethod
    def prepare(cls, app: Sanic):
        sync_manager = Manager()
        logger_queue = sync_manager.Queue(
            maxsize=app.config.LOGGING_QUEUE_MAX_SIZE
        )
        app.shared_ctx.logger_queue = logger_queue
        cls.update_cls_loggers(app.config.LOGGERS)

    @classmethod
    def setup(cls, app: Sanic):
        app.main_process_start(prepare_logger)
        app.main_process_ready(setup_logger)
        app.before_server_start(setup_server_logging)
        app.before_server_stop(remove_server_logging)
