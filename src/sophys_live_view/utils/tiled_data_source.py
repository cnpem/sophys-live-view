from collections import defaultdict
from time import time

from bluesky_tiled_plugins import BlueskyEventStream, BlueskyRun, CatalogOfBlueskyRuns
from bluesky_tiled_plugins.queries import TimeRange
from qtpy.QtCore import Qt, Signal, Slot
from tiled.client import from_uri

from .bluesky_data_source import BlueskyDataSource


class TiledDataSource(BlueskyDataSource):
    queue_event_read = Signal(str, BlueskyEventStream, str)  # uid, stream, signal name

    def __init__(self, tiled_url: str, hour_offset: float | None = None):
        super().__init__()

        self._url = tiled_url
        self._hour_offset = hour_offset

        self._run_cache = dict()
        self._requested_data: dict[str, dict[str, bool]] = defaultdict(
            lambda: defaultdict(lambda: False)
        )

    @Slot(str, BlueskyRun, str, str)
    def _read_signal_data(self, uid: str, stream: BlueskyEventStream, signal_name: str):
        print(f"Reading data for {signal_name}...")
        try:
            data = stream[signal_name].read()
        except RuntimeError:
            return

        self.notify_new_data_received(uid, len(data), {signal_name: data}, {})
        self.dispatch_data.emit()

    @Slot(str, str)
    def handle_data_request(self, uid: str, signal_name: str):
        if self._requested_data[uid][signal_name]:
            return
        self._requested_data[uid][signal_name] = True

        run = self._run_cache[uid]

        for stream_name in run.keys():
            if stream_name != "primary":
                continue

            stream = run[stream_name]

            if signal_name in stream.keys():
                self.queue_event_read.emit(uid, stream, signal_name)

    def process_run(self, uid: str, run: BlueskyRun):
        self("start", run.start)

        for stream_name in run.keys():
            if stream_name != "primary":
                continue

            stream = run[stream_name]
            self(
                "descriptor",
                {
                    "run_start": uid,
                    "name": stream_name,
                    **stream.metadata,
                },
            )

        self("stop", run.stop)

    def _start_processing(self):
        self.queue_event_read.connect(self._read_signal_data, Qt.QueuedConnection)
        self.data_requested.connect(self.handle_data_request)

        self._client = from_uri(self._url)

        if self._hour_offset is not None:
            time_offset = time() - self._hour_offset * 3600

            self.notify_loading_status("Loading Tiled data...", 0)

            n_runs = 0
            for catalog in self._client.values():
                if isinstance(catalog, CatalogOfBlueskyRuns):
                    old_runs_catalog = catalog.search(TimeRange(since=time_offset))

                    n_runs += len(old_runs_catalog)
                    for uid, run in old_runs_catalog.items():
                        self._run_cache[uid] = run

            for idx, (uid, run) in enumerate(self._run_cache.items()):
                try:
                    self.process_run(uid, run)
                except RuntimeError:
                    return

                self.notify_loading_status("Loading Tiled data...", 100 * idx / n_runs)

            self.notify_loading_status("Tiled data loaded.", 100)
            self.notify_go_to_last_automatically(True)

        super()._start_processing()

    def process(self):
        self.dispatch_data.emit()

    def close_thread(self):
        super().close_thread()

        self._client.context.close()
