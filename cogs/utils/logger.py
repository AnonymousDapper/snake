# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#

__all__ = "get_logger", "set_level"

import inspect
import logging
import os
from logging import handlers

# Make sure the log directory exists (and create it if not)
if not os.path.exists("logs"):
    os.makedirs("logs")

LOG_LEVEL = logging.INFO


class ConsoleFormatter(logging.Formatter):
    COLORS = (
        (logging.DEBUG, "\x1b[97;3m"),
        (logging.INFO, "\x1b[34m"),
        (logging.WARNING, "\x1b[93;1m"),
        (logging.ERROR, "\x1b[31;1m"),
        (logging.CRITICAL, "\x1b[41;37;1;5m"),
    )

    FORMATS = {
        level: logging.Formatter(
            f"\x1b[30;1m%(asctime)s\x1b[0m {color}%(levelname)-8s\x1b[0m \x1b[35m%(name)s:%(funcName)s\x1b[0m %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        for level, color in COLORS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno, self.FORMATS[logging.DEBUG])

        record.exc_text = None
        return formatter.format(record)


# Handlers
FILE_HANDLER = handlers.RotatingFileHandler(
    filename="logs/snake.log", maxBytes=1 * 1024 * 1024, backupCount=3
)  # Max size of 1Mb per-file, with 3 past files
FILE_FORMATTER = logging.Formatter(
    "%(asctime)s %(levelname)s | [%(module)s.%(funcName)s()] (%(filename)s:%(lineno)s)\n\t| %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
STREAM_HANDLER = logging.StreamHandler()


FILE_HANDLER.setLevel(logging.NOTSET)
FILE_HANDLER.setFormatter(FILE_FORMATTER)
STREAM_HANDLER.setFormatter(ConsoleFormatter())


# Set log level according to debug status (call once at init)
def set_level(debug=False):
    global LOG_LEVEL

    LOG_LEVEL = logging.DEBUG if debug else logging.INFO


# Special logger that runs for each module it's called in
def get_logger():
    # Get name of calling module
    call_frame = inspect.stack()[1]
    call_module = inspect.getmodule(call_frame[0])
    module_name = call_module.__name__

    module_logger = logging.getLogger(module_name)
    module_logger.setLevel(LOG_LEVEL)
    module_logger.addHandler(FILE_HANDLER)

    severe_stream_handler = logging.StreamHandler()
    severe_stream_handler.setLevel(logging.ERROR)
    severe_stream_handler.setFormatter(ConsoleFormatter())
    module_logger.addHandler(severe_stream_handler)

    del call_frame
    del call_module

    return module_logger


def get_console_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(STREAM_HANDLER)

    return logger
