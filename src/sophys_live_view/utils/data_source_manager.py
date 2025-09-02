from threading import Lock
import uuid

import numpy as np
from qtpy.QtCore import QThread, Signal

from .data_source import DataSource


class DataSourceManager(QThread):
    # Here, we have a UID referent to the DataSource from which the data originates from,
    # and a SubUID, which allows for differentiation between datasets from the same DataSource.
    # The idea is that we keep track of both separately so that we can do stuff like filtering
    # on the UI based on DataSource, for example.
    new_data_stream = Signal(
        str, str, str, set, dict
    )  # uid, subuid, display_name, fields, metadata
    new_data_received = Signal(
        str, str, dict, dict
    )  # uid, subuid, {signal : data}, {signal : metadata}

    def __init__(self):
        super().__init__()

        self._data_sources = dict()
        self._data_sources_lock = Lock()

    def add_data_source(self, data_source: DataSource):
        with self._data_sources_lock:
            self._data_sources[data_source] = str(uuid.uuid4())

            def new_data_stream_wrapper(uid, *args):
                self.new_data_stream.emit(self._data_sources[data_source], uid, *args)

            data_source.new_data_stream.connect(new_data_stream_wrapper)

            def new_data_received_wrapper(uid, *args):
                self.new_data_received.emit(self._data_sources[data_source], uid, *args)

            data_source.new_data_received.connect(new_data_received_wrapper)

    def run(self):
        # Here we should pull from data sources which do not provide us with asynchronous data.

        with self._data_sources_lock:
            data_source_uid = str(uuid.uuid4())

            uid = str(uuid.uuid4())
            self.new_data_stream.emit(
                data_source_uid, uid, "abc", {"timestamp", "det"}, {"uid": uid}
            )
            self.new_data_received.emit(
                data_source_uid,
                uid,
                {"timestamp": np.array([1, 2, 3]), "det": np.array([1, 2, 3])},
                {},
            )
            self.new_data_received.emit(
                data_source_uid,
                uid,
                {"timestamp": np.array([4, 5, 6]), "det": np.array([5, 6, 7])},
                {},
            )

            uid = str(uuid.uuid4())
            self.new_data_stream.emit(
                data_source_uid, uid, "def", {"timestamp", "det"}, {"uid": uid}
            )
            self.new_data_received.emit(
                data_source_uid,
                uid,
                {"timestamp": np.array([1, 2, 3]), "det": np.array([2, 2, 3])},
                {},
            )
            self.new_data_received.emit(
                data_source_uid,
                uid,
                {"timestamp": np.array([4, 5, 6]), "det": np.array([5, 6, 6])},
                {},
            )

            uid = str(uuid.uuid4())
            self.new_data_stream.emit(
                data_source_uid, uid, "ghi", {"timestamp", "det", "det2"}, {"uid": uid}
            )
            self.new_data_received.emit(
                data_source_uid,
                uid,
                {
                    "timestamp": np.array([1, 2, 3]),
                    "det": np.array([2, 1, 3]),
                    "det2": np.array([9, 8, 7]),
                },
                {},
            )
            self.new_data_received.emit(
                data_source_uid,
                uid,
                {
                    "timestamp": np.array([4, 5, 6]),
                    "det": np.array([5, 9, 6]),
                    "det2": np.array([1, 2, 3]),
                },
                {},
            )

            for data_source in self._data_sources:
                if hasattr(data_source, "start_thread"):
                    data_source.start_thread()
                else:
                    data_source.start()

    def stop(self):
        with self._data_sources_lock:
            for data_source in self._data_sources:
                data_source.terminate()
                data_source.wait()
