import time
from uuid import uuid4

import numpy as np
import pytest
from qtpy.QtCore import QObject, Signal

from sophys_live_view.utils.bluesky_data_source import DataSource
from sophys_live_view.utils.data_source_manager import DataSourceManager
from sophys_live_view.widgets import PlotDisplay


class BigStreamsDataSource(DataSource):
    def __init__(
        self, signals_per_event: int, events_per_stream: int, number_of_streams: int
    ):
        super().__init__()

        self._signals_per_event = signals_per_event
        self._events_per_stream = events_per_stream
        self._number_of_streams = number_of_streams

    def run(self):
        def _send_stream():
            uid = str(uuid4())

            signals = {f"signal_{n}" for n in range(self._signals_per_event)}
            self.new_data_stream.emit(
                uid,
                "Stream",
                signals,
                {},
                {},
                [],
                {},
            )

            for i in range(self._events_per_stream):
                data = {
                    f"signal_{n}": np.array([i]) for n in range(self._signals_per_event)
                }
                self.new_data_received.emit(uid, data, {})

            self.data_stream_closed.emit(uid)

        for _ in range(self._number_of_streams):
            _send_stream()

    def total_number_of_events(self):
        return self._events_per_stream * self._number_of_streams

    def close_thread(self):
        assert not self.isRunning()


@pytest.fixture
def empty_manager():
    manager = DataSourceManager(polling_time=0.05)

    yield manager

    if manager.isRunning():
        manager.stop()


class MockSignals(QObject):
    selected_streams_changed = Signal(list)
    selected_signals_changed_1d = Signal(str, set)
    selected_signals_changed_2d = Signal(str, str, set)
    custom_signal_added = Signal(str, str, str)


@pytest.fixture
def signals_mocker():
    return MockSignals()


@pytest.fixture
def display(empty_manager, signals_mocker, qtbot):
    display = PlotDisplay(
        empty_manager,
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
    empty_manager,
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
        empty_manager.add_data_source(data_source)
        empty_manager.start()

        _start_time = time.time()
        while (
            data_aggr.total_processed_data_events
            != data_source.total_number_of_events()
        ):
            if time.time() - _start_time >= 10.0:
                pytest.fail(
                    f"Timed out: Processed {data_aggr.total_processed_data_events} events."
                )

            qtbot.wait(25)

    assert __inner is None
