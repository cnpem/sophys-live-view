import pytest

from sophys_live_view.utils.json_data_source import JSONDataSource


def test_data_source_declare_stream(data_source_manager, dummy_data_source, qtbot):
    data_source_manager.add_data_source(dummy_data_source)
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()


def test_data_source_stream_data(data_source_manager, dummy_data_source, qtbot):
    data_source_manager.add_data_source(dummy_data_source)
    with qtbot.waitSignals([data_source_manager.new_data_received] * 4, timeout=1000):
        data_source_manager.start()


def test_data_source_stream_data_batched(
    data_source_manager, batched_dummy_data_source, qtbot
):
    data_source_manager.add_data_source(batched_dummy_data_source)
    with qtbot.waitSignals([data_source_manager.new_data_received] * 2, timeout=1000):
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
    data_source_manager, file_name, event_count, test_data_path, qtbot
):
    data_source = JSONDataSource(str(test_data_path / file_name))
    data_source._should_passthrough = True
    data_source_manager.add_data_source(data_source)

    with qtbot.waitSignals(
        [data_source_manager.new_data_received] * event_count, timeout=2000
    ):
        with qtbot.waitSignal(data_source_manager.new_data_stream, timeout=1000):
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
def test_bluesky_load_from_json_batching(
    data_source_manager, file_name, event_count, test_data_path, qtbot
):
    data_source = JSONDataSource(str(test_data_path / file_name))
    data_source._dispatch_time = 50  # Arbitrary time
    data_source_manager.add_data_source(data_source)

    with qtbot.waitSignal(
        data_source_manager.new_data_received, timeout=1000
    ) as blocker:
        with qtbot.waitSignal(data_source_manager.new_data_stream, timeout=1000):
            data_source_manager.start()

    _, _, number_of_events, received_data, _ = blocker.args

    assert all(
        [len(data_points) == number_of_events for data_points in received_data.values()]
    )
    assert number_of_events == event_count, (
        f"Got: {number_of_events} | Expected: {event_count}"
    )


def test_data_source_after_start(data_source_manager, test_data_path, qtbot):
    data_source_manager.start()

    data_source = JSONDataSource(str(test_data_path / "count_with_rand.json"))
    data_source._should_passthrough = True
    with qtbot.waitSignals([data_source_manager.new_data_received] * 50, timeout=2000):
        with qtbot.waitSignal(data_source_manager.new_data_stream, timeout=1000):
            data_source_manager.add_data_source(data_source)
