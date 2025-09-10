import pytest
from qtpy.QtCore import QObject, Signal

from sophys_live_view.widgets.plot_display import PlotDisplay


class MockSignals(QObject):
    selected_streams_changed = Signal(list)
    selected_signals_changed_1d = Signal(str, set)
    selected_signals_changed_2d = Signal(str, str, set)


@pytest.fixture
def signals_mocker():
    return MockSignals()


@pytest.fixture
def display(data_source_manager, signals_mocker, qtbot):
    display = PlotDisplay(
        data_source_manager,
        signals_mocker.selected_streams_changed,
        signals_mocker.selected_signals_changed_1d,
        signals_mocker.selected_signals_changed_2d,
    )
    qtbot.addWidget(display)
    return display


def test_plot_change_tab(display, qtbot):
    with qtbot.waitSignal(display.plot_tab_changed, timeout=1000) as blocker:
        display._plots.setCurrentIndex(1)
    assert "2D" in blocker.args[0], blocker.args

    with qtbot.waitSignal(display.plot_tab_changed, timeout=1000) as blocker:
        display._plots.setCurrentIndex(2)
    assert "2D" in blocker.args[0], blocker.args

    with qtbot.waitSignal(display.plot_tab_changed, timeout=1000) as blocker:
        display._plots.setCurrentIndex(0)
    assert "1D" in blocker.args[0], blocker.args


def test_plot_get_data(data_source_manager, display, qtbot):
    data_aggr = display._data_aggregator
    with qtbot.waitSignals([data_aggr.new_data_received] * 4, timeout=1000):
        data_source_manager.start()


def test_plot_draw_1d_curve(data_source_manager, display, signals_mocker, qtbot):
    uids_and_names = []

    data_source_manager.new_data_stream.connect(
        lambda uid, subuid, display_name, *_: uids_and_names.append(
            (subuid, display_name)
        )
    )

    data_aggr = display._data_aggregator
    with qtbot.waitSignals([data_aggr.new_data_received] * 4, timeout=1000):
        data_source_manager.start()

    signals_mocker.selected_streams_changed.emit(uids_and_names)
    signals_mocker.selected_signals_changed_1d.emit("timestamp", {"det", "det2"})

    def finished_building_plot():
        assert display._stacked_widget.currentWidget() is display._plots
        assert len(display._plots.widget(0).getItems()) == 3

    display.show()
    qtbot.waitExposed(display, timeout=1000)
    qtbot.waitUntil(finished_building_plot, timeout=1000)
