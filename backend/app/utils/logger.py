"""
ExecOS custom logger.

Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys


class ExecOSFormatter(logging.Formatter):
    """Coloured, typed log formatter."""

    LEVEL_COLOURS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self.LEVEL_COLOURS.get(record.levelno, "")
        grey = "\033[90m"
        level_tag = f"{colour}{self.BOLD}[{record.levelname}]{self.RESET}"
        location = f"{grey}{record.filename}:{record.lineno}{self.RESET}"
        body = record.getMessage()
        if record.exc_info:
            body = f"{body}\n{self.formatException(record.exc_info)}"
        return f"{level_tag} {location} — {body}"


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Return a namespaced ExecOS logger.

    Args:
        name: Typically __name__ of the calling module.
        level: Override log level (defaults to root level).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ExecOSFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    if level is not None:
        logger.setLevel(level)
    return logger


def configure_root(level: int = logging.INFO) -> None:
    """Configure the root logger with the ExecOS formatter.

    Call once at application startup (main.py).
    """
    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers:
        h.setFormatter(ExecOSFormatter())
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ExecOSFormatter())
        root.addHandler(handler)
