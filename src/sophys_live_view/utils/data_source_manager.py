from threading import Lock
import uuid

from qtpy.QtCore import QThread, Signal

from .data_source import DataSource


class DataSourceManager(QThread):
    # Here, we have a UID referent to the DataSource from which the data originates from,
    # and a SubUID, which allows for differentiation between datasets from the same DataSource.
    # The idea is that we keep track of both separately so that we can do stuff like filtering
    # on the UI based on DataSource, for example.
    new_data_stream = Signal(
        str, str, str, set, set, set, dict
    )  # uid, subuid, display_name, fields, detectors, motors, metadata
    new_data_received = Signal(
        str, str, dict, dict
    )  # uid, subuid, {signal : data}, {signal : metadata}
    go_to_last_automatically = Signal(str, bool)  # uid, state

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

            def go_to_last_automatically_wrapper(*args):
                self.go_to_last_automatically.emit(
                    self._data_sources[data_source], *args
                )

            data_source.go_to_last_automatically.connect(
                go_to_last_automatically_wrapper
            )

    def run(self):
        # Here we should pull from data sources which do not provide us with asynchronous data.

        with self._data_sources_lock:
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
