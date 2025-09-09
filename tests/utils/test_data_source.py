import pytest

from sophys_live_view.utils.data_source_manager import DataSourceManager
from sophys_live_view.utils.json_data_source import JSONDataSource


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
def test_bluesky_load_from_json(file_name, event_count, test_data_path, qtbot):
    manager = DataSourceManager()

    data_source = JSONDataSource(str(test_data_path / file_name))
    manager.add_data_source(data_source)

    with qtbot.waitSignals([manager.new_data_received] * event_count, timeout=2000):
        with qtbot.waitSignal(manager.new_data_stream, timeout=1000):
            manager.start()
