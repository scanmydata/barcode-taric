"""Κεντρικό logging + debugger για ορατότητα σφαλμάτων (AI/δίκτυο/matching).

Γράφει σε rotating αρχείο στο data-dir/logs/barcodetaric.log. Παρέχει επίσης έναν
in-memory ring buffer ώστε το GUI να δείχνει τα τελευταία events σε Debug panel.
"""

from __future__ import annotations

import logging
import logging.handlers
from collections import deque
from pathlib import Path

from .config import data_dir

_LOGGER: logging.Logger | None = None
_RING: deque[str] = deque(maxlen=500)


class _RingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _RING.append(self.format(record))
        except Exception:  # noqa: BLE001
            pass


def log_dir() -> Path:
    d = data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path() -> Path:
    return log_dir() / "barcodetaric.log"


def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    logger = logging.getLogger("barcodetaric")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    try:
        fh = logging.handlers.RotatingFileHandler(
            log_path(), maxBytes=512 * 1024, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass
    ring = _RingHandler()
    ring.setFormatter(fmt)
    logger.addHandler(ring)
    _LOGGER = logger
    return logger


def recent(limit: int = 200) -> list[str]:
    return list(_RING)[-limit:]


def clear_ring() -> None:
    _RING.clear()


def debug(msg: str) -> None:
    get_logger().debug(msg)


def info(msg: str) -> None:
    get_logger().info(msg)


def warning(msg: str) -> None:
    get_logger().warning(msg)


def error(msg: str) -> None:
    get_logger().error(msg)
