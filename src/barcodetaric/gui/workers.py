"""QThread workers — τρέχουν το pure-Python core εκτός UI thread.

Γενικός `Worker` που εκτελεί ένα callable και εκπέμπει progress/finished/failed.
Ένα προαιρετικό `progress_cb` περνιέται στο callable αν το δέχεται.
"""

from __future__ import annotations

import inspect
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal


class Worker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            params = inspect.signature(self._fn).parameters
            if "progress" in params and "progress" not in self._kwargs:
                self._kwargs["progress"] = self.progress.emit
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - surfaced στο UI
            self.failed.emit(f"{exc}\n{traceback.format_exc()}")


def run_async(parent: QObject, fn: Callable[..., Any], *args: Any,
              on_done: Callable[[Any], None] | None = None,
              on_error: Callable[[str], None] | None = None,
              on_progress: Callable[[str], None] | None = None,
              **kwargs: Any) -> tuple[QThread, Worker]:
    """Τρέχει το `fn` σε νέο QThread. Κρατά references ώστε να μη γίνει GC."""
    thread = QThread(parent)
    worker = Worker(fn, *args, **kwargs)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    if on_progress:
        worker.progress.connect(on_progress)

    def _cleanup() -> None:
        thread.quit()
        thread.wait()

    if on_done:
        worker.finished.connect(on_done)
    if on_error:
        worker.failed.connect(on_error)
    worker.finished.connect(lambda _: _cleanup())
    worker.failed.connect(lambda _: _cleanup())

    # Κράτα references στο parent για αποφυγή garbage-collection.
    if not hasattr(parent, "_active_workers"):
        parent._active_workers = []  # type: ignore[attr-defined]
    parent._active_workers.append((thread, worker))  # type: ignore[attr-defined]

    thread.start()
    return thread, worker
