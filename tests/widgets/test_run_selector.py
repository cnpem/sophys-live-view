import pytest
from qtpy.QtCore import QItemSelectionModel

from sophys_live_view.widgets.run_selector import RunListModel, RunSelector


@pytest.fixture
def selector(data_source_manager, qtbot):
    selector = RunSelector(data_source_manager)
    qtbot.addWidget(selector)
    return selector


def test_run_selector_basic_load(selector, data_source_manager, qtbot):
    assert selector._run_list_model.rowCount() == 0

    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    assert selector._run_list_model.rowCount() == 2
    index = selector._run_list_model.index(0)
    assert selector._run_list_model.data(index) == "abc"
    index = selector._run_list_model.index(1)
    assert selector._run_list_model.data(index) == "ghi"


def test_run_selector_select_one(selector, data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    with qtbot.waitSignal(selector.selected_streams_changed, timeout=1000) as blocker:
        index = selector._run_list_model.index(1)
        selector._run_list_view.setCurrentIndex(index)
    assert len(blocker.args[0]) == 1, blocker.args[0]
    assert blocker.args[0][0][1] == "ghi", blocker.args[0]


def test_run_selector_select_multiple(selector, data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    selection_model = selector._run_list_view.selectionModel()

    def select(row: int, flag: QItemSelectionModel.SelectionFlag):
        selection_model.select(selector._run_list_model.index(row), flag)

    with qtbot.waitSignal(selector.selected_streams_changed, timeout=1000):
        select(0, QItemSelectionModel.SelectionFlag.SelectCurrent)
    with qtbot.waitSignal(selector.selected_streams_changed, timeout=1000) as blocker:
        select(1, QItemSelectionModel.SelectionFlag.Toggle)

    args = blocker.args
    assert len(args[0]) == 2, args[0]
    assert args[0][0][1] == "abc", args[0]
    assert args[0][1][1] == "ghi", args[0]


def test_run_selector_bookmark(selector, data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    index = selector._run_list_model.index(1)

    assert not selector._run_list_model.data(index, RunListModel.BOOKMARK_ROLE)
    selector.toggle_bookmark(index)
    assert selector._run_list_model.data(index, RunListModel.BOOKMARK_ROLE)
    selector.toggle_bookmark(index)
    assert not selector._run_list_model.data(index, RunListModel.BOOKMARK_ROLE)
