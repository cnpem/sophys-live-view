import pytest
from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QTableWidget

from sophys_live_view.widgets.metadata_viewer import MetadataViewer


class MockSignals(QObject):
    selected_streams_changed = Signal(list)


@pytest.fixture
def signals_mocker():
    return MockSignals()


@pytest.fixture
def viewer(data_source_manager, signals_mocker, qtbot):
    selector = MetadataViewer(
        data_source_manager, signals_mocker.selected_streams_changed
    )
    qtbot.addWidget(selector)
    return selector


def test_acquire_metadata(viewer, data_source_manager, qtbot):
    name_to_uid = {}

    data_source_manager.new_data_stream.connect(
        lambda uid, subuid, display_name, *_: name_to_uid.update({display_name: subuid})
    )

    def metadata_complete():
        assert (
            viewer._stream_metadata.get(name_to_uid.get("abc"), {}).get(
                "stream_name", "missing"
            )
            == "abc"
        )
        assert (
            viewer._stream_metadata.get(name_to_uid.get("ghi"), {}).get(
                "stream_name", "missing"
            )
            == "ghi"
        )

    data_source_manager.start()
    qtbot.waitUntil(metadata_complete, timeout=1000)


def test_select_stream(viewer, data_source_manager, signals_mocker, qtbot):
    uids_and_names = []

    data_source_manager.new_data_stream.connect(
        lambda uid, subuid, display_name, *_: uids_and_names.append(
            (subuid, display_name)
        )
    )

    def tabs_populated():
        assert viewer._tab.count() == 2
        assert viewer._tab.tabText(0) == "abc"
        assert viewer._tab.tabText(1) == "ghi"

    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()

    signals_mocker.selected_streams_changed.emit(uids_and_names)
    qtbot.waitUntil(tabs_populated, timeout=1000)

    abc_page: QTableWidget = viewer._tab.widget(0)
    assert abc_page.rowCount() == 2
    assert abc_page.item(0, 0).text() == "stream_name"
    assert abc_page.item(0, 1).text() == "abc"
    assert abc_page.item(1, 0).text() == "uid"

    ghi_page: QTableWidget = viewer._tab.widget(1)
    assert ghi_page.rowCount() == 4
    assert ghi_page.item(0, 0).text() == "stream_name"
    assert ghi_page.item(0, 1).text() == "ghi"
    assert ghi_page.item(1, 0).text() == "uid"
    assert ghi_page.item(2, 0).text() == "configuration - one"
    assert ghi_page.item(2, 1).text() == "ghi"
    assert ghi_page.item(3, 0).text() == "configuration - two - three"
    assert ghi_page.item(3, 1).text() == "ghi"
