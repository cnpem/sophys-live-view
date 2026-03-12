import pytest

from sophys_live_view.utils.data_source_manager import DataSourceManager
from sophys_live_view.utils.json_data_source import JSONDataSource


@pytest.fixture
def empty_manager():
    manager = DataSourceManager(polling_time=0.05)

    yield manager

    if manager.isRunning():
        manager.stop()


def test_data_source_declare_stream(data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()


def test_data_source_stream_data(data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_received] * 4, timeout=1000):
        data_source_manager.start()


@pytest.mark.parametrize(
    "file_name,event_count",
    [
        ("count_with_rand.json", 50),
        ("scan_with_rand.json", 11),
        ("scan_with_det.json", 21),
        ("grid_with_rand.json", 121),
        ("grid_with_det.json", 231),
    ],
)
def test_bluesky_load_from_json(
    empty_manager, file_name, event_count, test_data_path, qtbot
):
    data_source = JSONDataSource(str(test_data_path / file_name))
    empty_manager.add_data_source(data_source)

    with qtbot.waitSignals(
        [empty_manager.new_data_received] * event_count, timeout=2000
    ):
        with qtbot.waitSignal(empty_manager.new_data_stream, timeout=1000):
            empty_manager.start()


def test_data_source_after_start(empty_manager, test_data_path, qtbot):
    empty_manager.start()

    data_source = JSONDataSource(str(test_data_path / "count_with_rand.json"))
    with qtbot.waitSignals([empty_manager.new_data_received] * 50, timeout=2000):
        with qtbot.waitSignal(empty_manager.new_data_stream, timeout=1000):
            empty_manager.add_data_source(data_source)
