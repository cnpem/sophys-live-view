import uuid

import numpy as np
import pytest

from sophys_live_view.utils.data_source import DataSource
from sophys_live_view.utils.data_source_manager import DataSourceManager


class DummyDataSource(DataSource):
    def run(self):
        uid = str(uuid.uuid4())
        self.new_data_stream.emit(
            uid,
            "abc",
            {"timestamp", "det"},
            {},
            set(("det",)),
            ["timestamp"],
            {"uid": uid},
        )
        self.new_data_received.emit(
            uid,
            {"timestamp": np.array([1, 2, 3]), "det": np.array([1, 2, 3])},
            {},
        )
        self.new_data_received.emit(
            uid,
            {"timestamp": np.array([4, 5, 6]), "det": np.array([5, 6, 7])},
            {},
        )

        uid = str(uuid.uuid4())
        self.new_data_stream.emit(
            uid,
            "ghi",
            {"timestamp", "det", "det2"},
            {},
            set(("det2",)),
            ["timestamp"],
            {"uid": uid},
        )
        self.new_data_received.emit(
            uid,
            {
                "timestamp": np.array([1, 2, 3]),
                "det": np.array([2, 1, 3]),
                "det2": np.array([9, 8, 7]),
            },
            {},
        )
        self.new_data_received.emit(
            uid,
            {
                "timestamp": np.array([4, 5, 6]),
                "det": np.array([5, 9, 6]),
                "det2": np.array([1, 2, 3]),
            },
            {},
        )


@pytest.fixture
def data_source_manager():
    manager = DataSourceManager()
    manager.add_data_source(DummyDataSource())
    yield manager
    manager.stop()
