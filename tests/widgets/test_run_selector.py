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

    selection_model = selector._run_list.selectionModel()

    def select(row: int, flag: QItemSelectionModel.SelectionFlag):
        selection_model.select(
            selector._run_list.indexFromItem(selector._run_list.item(row)), flag
        )

    with qtbot.waitSignal(selector.selected_streams_changed, timeout=1000):
        select(0, QItemSelectionModel.SelectionFlag.SelectCurrent)
    with qtbot.waitSignal(selector.selected_streams_changed, timeout=1000) as blocker:
        select(1, QItemSelectionModel.SelectionFlag.Toggle)

    args = blocker.args
    assert len(args[0]) == 2, args[0]
    assert args[0][0][1] == "abc", args[0]
    assert args[0][1][1] == "ghi", args[0]
