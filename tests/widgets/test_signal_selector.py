import pytest
from qtpy.QtCore import QObject, Signal

from sophys_live_view.widgets.signal_selector import SignalSelector


class MockSignals(QObject):
    selected_streams_changed = Signal(list)


@pytest.fixture
def signals_mocker():
    return MockSignals()


@pytest.fixture
def selector(data_source_manager, signals_mocker, qtbot):
    selector = SignalSelector(
        data_source_manager, signals_mocker.selected_streams_changed
    )
    qtbot.addWidget(selector)
    return selector


def test_default_signals_1d(data_source_manager, selector, signals_mocker, qtbot):
    uids_and_names = []

    data_source_manager.new_data_stream.connect(
        lambda uid, subuid, display_name, *_: uids_and_names.append(
            (subuid, display_name)
        )
    )
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    with qtbot.waitSignal(
        selector.selected_signals_changed_1d, timeout=1000
    ) as blocker:
        signals_mocker.selected_streams_changed.emit(uids_and_names[:1])

    assert blocker.args[0] == "timestamp", blocker.args
    assert "det" in blocker.args[1], blocker.args


def test_change_signals_1d(data_source_manager, selector, signals_mocker, qtbot):
    uids_and_names = []

    data_source_manager.new_data_stream.connect(
        lambda uid, subuid, display_name, *_: uids_and_names.append(
            (subuid, display_name)
        )
    )
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    with qtbot.waitSignal(
        selector.selected_signals_changed_1d, timeout=1000
    ) as blocker:
        signals_mocker.selected_streams_changed.emit(uids_and_names[:1])

    assert "timestamp" not in blocker.args[1], blocker.args

    with qtbot.waitSignal(
        selector.selected_signals_changed_1d, timeout=1000
    ) as blocker:
        selector._1d_signal_selection_table.cellWidget(1, 2).click()

    assert blocker.args[0] == "timestamp", blocker.args
    assert "det" in blocker.args[1], blocker.args
    assert "timestamp" in blocker.args[1], blocker.args


def test_add_custom_signal(data_source_manager, selector, qtbot):
    uids_and_names = []

    data_source_manager.new_data_stream.connect(
        lambda uid, subuid, display_name, *_: uids_and_names.append(
            (subuid, display_name)
        )
    )
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    with qtbot.waitSignal(selector.custom_signal_added, timeout=1000):
        selector._add_custom_signal(uids_and_names[0][0], "test", "123")

    assert "test" in selector.uids_with_signal
    assert uids_and_names[0][0] in selector.uids_with_signal["test"]
