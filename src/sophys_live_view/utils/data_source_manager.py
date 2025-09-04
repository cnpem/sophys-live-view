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

        self._unvisited_data_sources = set()
        self._visited_data_sources = set()

    def add_data_source(self, data_source: DataSource):
        with self._data_sources_lock:
            data_source_uid = str(uuid.uuid4())
            self._data_sources[data_source_uid] = data_source

            def new_data_stream_wrapper(uid, *args):
                self.new_data_stream.emit(data_source_uid, uid, *args)

            data_source.new_data_stream.connect(new_data_stream_wrapper)

            def new_data_received_wrapper(uid, *args):
                self.new_data_received.emit(data_source_uid, uid, *args)

            data_source.new_data_received.connect(new_data_received_wrapper)

            def go_to_last_automatically_wrapper(*args):
                self.go_to_last_automatically.emit(data_source_uid, *args)

            data_source.go_to_last_automatically.connect(
                go_to_last_automatically_wrapper
            )

            self._unvisited_data_sources.add(data_source_uid)

    def run(self):
        # Here we should pull from data sources which do not provide us with asynchronous data.

        while not self.isInterruptionRequested():
            self.sleep(0.2)

            with self._data_sources_lock:
                if len(self._unvisited_data_sources) == 0:
                    continue

                data_source_uid = self._unvisited_data_sources.pop()
                data_source = self._data_sources[data_source_uid]

                data_source.start_thread()

                self._visited_data_sources.add(data_source_uid)

    def stop(self):
        with self._data_sources_lock:
            for data_source in self._data_sources.values():
                data_source.close_thread()
                data_source.wait()

            self.requestInterruption()
