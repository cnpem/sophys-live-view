from collections import deque
import pathlib
import uuid

import pytest

from sophys_live_view.utils.data_source import BatchReceivedDataSource, DataSource
from sophys_live_view.utils.data_source_manager import DataSourceManager


class DummyDataSourceData:
    def __iter__(self):
        for type_index in self._order:
            if type_index == 0:
                uid = str(uuid.uuid4())

            signal_name, arguments_list = self._data[type_index]
            yield signal_name, (uid, *arguments_list.popleft())

    def __init__(self):
        self.new_data_stream = deque(
            (
                (
                    "abc",
                    {"timestamp", "det"},
                    {},
                    set(("det",)),
                    ["timestamp"],
                    {"stream_name": "abc"},
                ),
                (
                    "ghi",
                    {"timestamp", "det", "det2"},
                    {},
                    set(("det2",)),
                    ["timestamp"],
                    {
                        "stream_name": "ghi",
                        "configuration": {"one": "ghi", "two": {"two_three": "ghi"}},
                    },
                ),
            )
        )

        self.new_data_received = deque(
            (
                (
                    3,
                    {"timestamp": [1, 2, 3], "det": [1, 2, 3]},
                    {},
                ),
                (
                    3,
                    {"timestamp": [4, 5, 6], "det": [5, 6, 7]},
                    {},
                ),
                (
                    3,
                    {
                        "timestamp": [1, 2, 3],
                        "det": [2, 1, 3],
                        "det2": [9, 8, 7],
                    },
                    {},
                ),
                (
                    3,
                    {
                        "timestamp": [4, 5, 6],
                        "det": [5, 9, 6],
                        "det2": [1, 2, 3],
                    },
                    {},
                ),
            )
        )

        self.data_stream_closed = deque(((), ()))

        self._order = (0, 1, 1, 2, 0, 1, 1, 2)
        self._data = (
            ("new_data_stream", self.new_data_stream),
            ("new_data_received", self.new_data_received),
            ("data_stream_closed", self.data_stream_closed),
        )


class DummyDataSource(DataSource):
    def process(self):
        _data = DummyDataSourceData()

        for signal_name, arguments in _data:
            getattr(self, signal_name).emit(*arguments)


class BatchedDummyDataSource(BatchReceivedDataSource):
    def process(self):
        _data = DummyDataSourceData()

        for signal_name, arguments in _data:
            getattr(self, "notify_" + signal_name)(*arguments)


@pytest.fixture
def dummy_data_source():
    return DummyDataSource()


@pytest.fixture
def batched_dummy_data_source():
    return BatchedDummyDataSource()


@pytest.fixture
def data_source_manager():
    manager = DataSourceManager(polling_time=0.05)

    yield manager

    manager.stop()


@pytest.fixture(scope="session")
def test_data_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "runs"
