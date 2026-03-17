from collections.abc import MutableSequence
from dataclasses import dataclass
from functools import wraps
from typing import TypeAlias, Union

from qtpy.QtCore import Qt, QThread, QTimer, Signal, Slot

from .thread_utils import _ProxyThreadObject, is_main_thread

DATA_RECEIVED_DATA_TYPE: TypeAlias = dict[str, MutableSequence]
DATA_RECEIVED_METADATA_TYPE: TypeAlias = dict[str, dict[str, MutableSequence]]


class DataSource(QThread):
    """
    The base for any DataSource, containing the required signals and some common functionality.
    """

    new_data_stream = Signal(
        str, str, set, dict, set, list, dict
    )  # uid, display_name, fields, fields name map, detectors, motors, metadata
    new_data_received = Signal(
        str, int, dict, dict
    )  # uid, number of events, {signal : data}, {signal : metadata}
    data_stream_closed = Signal(str)  # uid
    go_to_last_automatically = Signal(bool)  # Whether to auto-update the display or not
    loading_status = Signal(str, float)  # status message, completion percentage

    def notify_new_data_stream(
        self,
        uid: str,
        display_name: str,
        fields: set[str],
        fields_name_map: dict[str, str],
        detectors: set[str],
        motors: list[str],
        metadata: dict,
    ) -> None:
        self.new_data_stream.emit(
            uid, display_name, fields, fields_name_map, detectors, motors, metadata
        )

    def notify_new_data_received(
        self,
        uid: str,
        number_of_events: int,
        data: DATA_RECEIVED_DATA_TYPE,
        metadata: DATA_RECEIVED_METADATA_TYPE,
    ) -> None:
        self.new_data_received.emit(uid, number_of_events, data, metadata)

    def notify_data_stream_closed(self, uid: str) -> None:
        self.data_stream_closed.emit(uid)

    def notify_go_to_last_automatically(self, auto_update: bool) -> None:
        self.go_to_last_automatically.emit(auto_update)

    def notify_loading_status(
        self, status_message: str, completion_percentage: float
    ) -> None:
        self.loading_status.emit(status_message, completion_percentage)

    def __init__(self):
        super().__init__()

        self.__inner_obj = _ProxyThreadObject(self, self.process)

    @Slot()
    def process(self):
        """Method to process data for this DataSource."""
        raise NotImplementedError

    def start_thread(self):
        """Start processing this DataSource."""
        QThread.start(self)

    def close_thread(self):
        """Stop processing this DataSource."""
        QThread.quit(self)


def _ensure_dispatch_timer(func):
    """
    Helper for BatchReceivedDataMixin to create ensure a dispatch timer exists when entering a method.

    This needs to be done so that the dispatch timer is created in the appropriate thread context, which
    is why it cannot be created on __init__ (which is ran in the main thread).
    """

    @wraps(func)
    def __inner(self, *args, **kwargs):
        __tracebackhide__ = True
        if not hasattr(self, "_dispatch_timer") and not self._should_passthrough:
            self._dispatch_timer = QTimer(singleShot=True)
            self._dispatch_timer.timeout.connect(
                self._dispatch_data, type=Qt.ConnectionType.DirectConnection
            )

        return func(self, *args, **kwargs)

    return __inner


class BatchReceivedDataSource(DataSource):
    """
    DataSource subclass that batches received data in order to reduce
    the amount of signals emitted and data copy.

    This is primarily a performance optimization for fast data retrieval,
    but it does increase the latency in receiving new data.
    """

    @dataclass
    class BatchContainerItem:
        number_of_events: int
        data: DATA_RECEIVED_DATA_TYPE
        metadata: DATA_RECEIVED_METADATA_TYPE

        def __iter__(self):
            return iter((self.number_of_events, self.data, self.metadata))

    BATCH_CONTAINER_TYPE: TypeAlias = dict[str, BatchContainerItem]

    def __init__(self, dispatch_time_ms: int = 50):
        super().__init__()

        self._should_passthrough = (
            False  # Testing helper for passing data directly through, without batching.
        )
        self._dispatch_time = dispatch_time_ms

        self._batch_container: self.BATCH_CONTAINER_TYPE = dict()

    @_ensure_dispatch_timer
    def notify_new_data_received(
        self,
        uid: str,
        number_of_events: int,
        data: DATA_RECEIVED_DATA_TYPE,
        metadata: DATA_RECEIVED_METADATA_TYPE,
    ):
        if self._should_passthrough:
            return super().notify_new_data_received(
                uid, number_of_events, data, metadata
            )

        if uid not in self._batch_container:
            self._batch_container[uid] = self.BatchContainerItem(
                number_of_events, data, metadata
            )
        else:
            self._batch_container[uid].number_of_events += number_of_events
            self._extend_sequences_in_map(self._batch_container[uid].data, data)
            self._extend_sequences_in_map(self._batch_container[uid].metadata, metadata)

        if not self._dispatch_timer.isActive():
            self._dispatch_timer.start(self._dispatch_time)

    _RECURSIVE_DICT_TYPE: TypeAlias = dict[
        str, Union[MutableSequence, "_RECURSIVE_DICT_TYPE"]
    ]

    def _extend_sequences_in_map(
        self, original_map: _RECURSIVE_DICT_TYPE, map_to_append: _RECURSIVE_DICT_TYPE
    ):
        """Recursively extends mutable sequences inside a dict scructure."""
        original_keys = set(original_map.keys())
        to_append_keys = set(map_to_append.keys())

        common_keys = original_keys & to_append_keys
        for key in common_keys:
            if isinstance(original_map[key], MutableSequence):
                assert isinstance(map_to_append[key], MutableSequence)
                original_map[key].extend(map_to_append[key])
                continue

            if isinstance(original_map[key], dict):
                assert isinstance(map_to_append[key], dict)
                self._extend_sequences_in_map(original_map[key], map_to_append[key])
                continue

        new_keys = to_append_keys - original_keys
        for key in new_keys:
            original_map[key] = map_to_append[key]

    @Slot()
    def _dispatch_data(self):
        assert not is_main_thread(QThread.currentThread()), (
            "Running processing in main thread!"
        )

        for uid, (number_of_events, data, metadata) in self._batch_container.items():
            self.new_data_received.emit(uid, number_of_events, data, metadata)

        self._batch_container.clear()
