import time
from uuid import uuid4

import pytest
from qtpy.QtCore import QObject, Signal

from sophys_live_view.utils.bluesky_data_source import BatchReceivedDataSource
from sophys_live_view.widgets import PlotDisplay


class BigStreamsDataSource(BatchReceivedDataSource):
    def __init__(
        self, signals_per_event: int, events_per_stream: int, number_of_streams: int
    ):
        super().__init__()

        self._signals_per_event = signals_per_event
        self._events_per_stream = events_per_stream
        self._number_of_streams = number_of_streams

    def process(self):
        empty_dict = {}

        def _send_stream():
            uid = str(uuid4())

            signals = {f"signal_{n}" for n in range(self._signals_per_event)}
            self.notify_new_data_stream(
                uid,
                "Stream",
                signals,
                {},
                set(),
                [],
                {},
            )

            for i in range(self._events_per_stream):
                data = {f"signal_{n}": [i] for n in range(self._signals_per_event)}
                self.notify_new_data_received(uid, 1, data, empty_dict)

            self.notify_data_stream_closed(uid)

        for _ in range(self._number_of_streams):
            _send_stream()

            self.dispatch_data.emit()

    def total_number_of_events(self):
        return self._events_per_stream * self._number_of_streams


class MockSignals(QObject):
    selected_streams_changed = Signal(list)
    selected_signals_changed_1d = Signal(str, set)
    selected_signals_changed_2d = Signal(str, str, set)
    custom_signal_added = Signal(str, str, str)


@pytest.fixture
def signals_mocker():
    return MockSignals()


@pytest.fixture
def display(data_source_manager, signals_mocker, qtbot):
    display = PlotDisplay(
        data_source_manager,
        signals_mocker.selected_streams_changed,
        signals_mocker.selected_signals_changed_1d,
        signals_mocker.selected_signals_changed_2d,
        signals_mocker.custom_signal_added,
    )
    qtbot.addWidget(display)
    return display


@pytest.mark.benchmark(
    max_time=10.0,
    warmup=False,
)
@pytest.mark.parametrize(
    ("signals_per_event", "events_per_stream", "number_of_streams"),
    ((2, 1000, 10), (10, 1000, 2), (2, 10000, 1), (20, 10000, 1), (200, 1000, 1)),
)
def test_big_streams(
    signals_per_event,
    events_per_stream,
    number_of_streams,
    benchmark,
    data_source_manager,
    display,
    qtbot,
):
    data_aggr = display._data_aggregator

    @benchmark
    def __inner():
        data_aggr.total_processed_data_events = 0

        data_source = BigStreamsDataSource(
            signals_per_event, events_per_stream, number_of_streams
        )
        data_source_manager.add_data_source(data_source)
        data_source_manager.start()

        _start_time = time.time()
        while (
            data_aggr.total_processed_data_events
            != data_source.total_number_of_events()
        ):
            if time.time() - _start_time >= 10.0:
                pytest.fail(
                    f"Timed out: Processed {data_aggr.total_processed_data_events} events out of {data_source.total_number_of_events()}."
                )

            qtbot.wait(25)

    assert __inner is None
