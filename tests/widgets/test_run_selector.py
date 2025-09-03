import pytest
from qtpy.QtCore import QItemSelectionModel

from sophys_live_view.widgets.run_selector import RunSelector


@pytest.fixture
def selector(data_source_manager, qtbot):
    selector = RunSelector(data_source_manager)
    qtbot.addWidget(selector)
    return selector


def test_run_selector_basic_load(selector, data_source_manager, qtbot):
    assert selector._run_list.count() == 0

    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    assert selector._run_list.count() == 2
    assert selector._run_list.item(0).text() == "abc"
    assert selector._run_list.item(1).text() == "ghi"


def test_run_selector_select_one(selector, data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    with qtbot.waitSignal(selector.selected_streams_changed, timeout=1000) as blocker:
        selector._run_list.setCurrentRow(
            1, QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
    assert len(blocker.args[0]) == 1, blocker.args[0]
    assert blocker.args[0][0][1] == "ghi", blocker.args[0]


def test_run_selector_select_multiple(selector, data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    with qtbot.waitSignal(selector.selected_streams_changed, timeout=1000) as blocker:
        selector._run_list.setCurrentRow(
            0, QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        selector._run_list.setCurrentRow(1, QItemSelectionModel.SelectionFlag.Select)
    assert len(blocker.args[0]) == 2, blocker.args[0]
    assert blocker.args[0][0][1] == "abc", blocker.args[0]
    assert blocker.args[0][1][1] == "ghi", blocker.args[0]
