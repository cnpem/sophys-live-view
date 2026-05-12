from collections.abc import Callable

from qtpy.QtCore import QCoreApplication, QObject, Qt, QThread, Slot


def is_main_thread(thread: QThread) -> bool:
    instance = QCoreApplication.instance()
    assert instance is not None, "No QCoreApplication running."
    return thread is instance.thread()


class _ProxyThreadObject(QObject):
    """Helper object for ensuring some function is called within its expected thread context."""

    def __init__(
        self,
        thread: QThread,
        started_proc_slot: Callable | None = None,
        finished_proc_slot: Callable | None = None,
    ):
        super().__init__()

        self.moveToThread(thread)

        def do_nothing():
            pass

        self._started_proc_slot = (
            started_proc_slot or do_nothing
        )  # Help with type hints
        if started_proc_slot is not None:
            thread.started.connect(
                self._on_started, type=Qt.ConnectionType.QueuedConnection
            )

        self._finished_proc_slot = (
            finished_proc_slot or do_nothing
        )  # Help with type hints
        if finished_proc_slot is not None:
            thread.finished.connect(
                self._on_finished, type=Qt.ConnectionType.QueuedConnection
            )

    @Slot()
    def _on_started(self):
        assert not is_main_thread(QThread.currentThread()), (
            "Running processing in main thread!"
        )

        self._started_proc_slot()

    @Slot()
    def _on_finished(self):
        assert not is_main_thread(QThread.currentThread()), (
            "Running processing in main thread!"
        )

        self._finished_proc_slot()
