from collections import defaultdict

import numpy as np
from qtpy.QtCore import QObject, Qt, QTimer, Signal
from qtpy.QtWidgets import QLabel, QStackedWidget, QTabWidget, QVBoxLayout
from silx.gui.colors import Colormap
from silx.gui.plot.PlotWindow import Plot1D, Plot2D

from .interfaces import IPlotDisplay
from .plot_actions import DerivativeAction


class DataAggregator(QObject):
    new_data_received = Signal(str)  # subuid

    def __init__(self, new_stream_signal: Signal, new_data_signal: Signal):
        """
        Aggregate received data into useful containers.

        Parameters
        ----------
        new_stream_signal : Signal
            Signal that will be emitted when a new stream has been created.
        new_data_signal : Signal
            Signal that will be emitted when new data for a stream has been received.
        """
        super().__init__()

        self._data_cache = defaultdict(lambda: defaultdict(lambda: np.array([[], []])))
        self._metadata_cache = defaultdict(lambda: dict())
        self._signals_name_map = defaultdict(lambda: dict())
        self._custom_signals_map = defaultdict(lambda: dict())

        new_stream_signal.connect(self._on_new_stream)
        new_data_signal.connect(self._receive_new_data)

    def get_data(self, uid: str, signal_name: str):
        return self._data_cache[uid].get(signal_name, None)

    def get_metadata(self, uid: str):
        return self._metadata_cache[uid]

    def get_signal_name(self, uid: str, signal: str):
        return self._signals_name_map[uid].get(signal, signal)

    def get_signals(self, uid: str) -> set[str]:
        return set(self._data_cache[uid].keys())

    def add_custom_signal(self, uid: str, name: str, expression: str):
        self._custom_signals_map[uid][name] = expression

        environment = {"np": np}
        for detector, value in self._data_cache[uid].items():
            environment[detector] = value

        try:
            self._data_cache[uid][name] = eval(expression, locals=environment)
        except Exception:
            print(f"The provided expression '{expression}' is not valid.")

    def _on_new_stream(
        self,
        uid: str,
        subuid: str,
        display_name: str,
        signals: set[str],
        signals_name_map: dict[str, str],
        detectors: set[str],
        motors: list[str],
        metadata: dict,
    ):
        self._metadata_cache[subuid] = metadata
        self._signals_name_map[subuid] = signals_name_map

        if "shape" in metadata:
            for detector in metadata.get("detectors", []):
                self._data_cache[subuid][detector] = np.ones(metadata["shape"]) * np.nan

    def _receive_new_data(self, uid: str, subuid: str, new_data: dict, metadata: dict):
        for detector_name, detector_values in new_data.items():
            if detector_name in metadata and "position" in metadata[detector_name]:
                position = metadata[detector_name]["position"]
                self._data_cache[subuid][detector_name][position] = detector_values
            else:
                self._data_cache[subuid][detector_name] = np.append(
                    self._data_cache[subuid][detector_name], detector_values
                )

        for name, expression in self._custom_signals_map[subuid].items():
            self.add_custom_signal(subuid, name, expression)

        self.new_data_received.emit(subuid)


class PlotDisplay(IPlotDisplay):
    def __init__(
        self,
        data_source_manager,
        selected_streams_changed: Signal,
        selected_signals_changed_1d: Signal,
        selected_signals_changed_2d: Signal,
        custom_signal_added: Signal,
        show_stats_by_default: bool = False,
    ):
        super().__init__()

        self._current_uids = [("", "")]

        self._1d_x_axis_names = defaultdict(lambda: "")
        self._1d_y_axis_names = defaultdict(lambda: set())

        self._2d_x_axis_names = defaultdict(lambda: "")
        self._2d_y_axis_names = defaultdict(lambda: "")
        self._2d_z_axis_names = defaultdict(lambda: set())

        layout = QVBoxLayout()
        self._stacked_widget = QStackedWidget()
        layout.addWidget(self._stacked_widget)
        self.setLayout(layout)

        standby_label = QLabel("Waiting for a run to be selected...")
        standby_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
        )
        self._stacked_widget.addWidget(standby_label)

        self._plots = QTabWidget()
        _plot_1d = Plot1D()
        _plot_1d.setDefaultPlotPoints(True)
        _plot_1d.toolBar().addAction(DerivativeAction(_plot_1d, _plot_1d))
        self._plots.addTab(_plot_1d, "1D")

        if show_stats_by_default:
            dock_widget = _plot_1d.getStatsWidget().parent()
            # Run the callback that adds the widget to its docking area.
            dock_widget.show()
            # By default, it adds the dock widget to the right area. We need it at the bottom.
            _plot_1d.removeDockWidget(dock_widget)
            _plot_1d.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_widget)
            # It was hidden when we removed the dock widget from its parent.
            dock_widget.show()

        _plot_2d_scatter = Plot2D()
        _plot_2d_scatter.setDefaultColormap(Colormap(name="viridis"))
        self._plots.addTab(_plot_2d_scatter, "2D - Scatter")

        _plot_2d_grid = Plot2D()
        _plot_2d_grid.setDefaultColormap(Colormap(name="viridis"))
        self._plots.addTab(_plot_2d_grid, "2D - Grid")

        self._stacked_widget.addWidget(self._plots)

        self._data_aggregator = DataAggregator(
            data_source_manager.new_data_stream,
            data_source_manager.new_data_received,
        )
        self._data_aggregator.new_data_received.connect(self._update_plots_maybe)

        # NOTE: Here we have kind of a race condition: We need the change_stream_signal
        # connection, but it must happen before the other ones, so that the signal selector
        # signals update the plots with the correct information.
        selected_streams_changed.connect(self.change_current_streams)
        selected_signals_changed_1d.connect(
            self._on_1d_signals_changed, Qt.ConnectionType.QueuedConnection
        )
        selected_signals_changed_2d.connect(
            self._on_2d_signals_changed, Qt.ConnectionType.QueuedConnection
        )
        custom_signal_added.connect(self._on_custom_signal_added)

        self._plots.currentChanged.connect(self._on_plot_tab_changed)

        self._plot_update_timer = QTimer()
        self._plot_update_timer.setSingleShot(True)
        self._plot_update_timer.setInterval(50)
        self._plot_update_timer.timeout.connect(self._update_plots)

    def _update_plots_maybe(self, changed_uid: str):
        uids = set(i[0] for i in self._current_uids)
        if changed_uid in uids:
            self.update_plots()

    def update_plots(self):
        self._plot_update_timer.start()

    def _update_plots(self):
        self.change_current_streams(self._current_uids)

    def change_current_streams(self, new_uids_and_names: list[tuple[str, str]]):
        self._current_uids = new_uids_and_names

        if len(new_uids_and_names) == 1 and new_uids_and_names[0][0] == "":
            self._stacked_widget.setCurrentIndex(0)
            return

        self._plots.widget(0).clear()
        self._plots.widget(1).clear()
        self._plots.widget(2).clear()

        for uid, stream_name in new_uids_and_names:
            self._stacked_widget.setCurrentWidget(self._plots)

            signals = self._data_aggregator.get_signals(uid)

            if self._plots.widget(0).isVisible():
                for detector_name in sorted(signals):
                    if detector_name not in self._1d_y_axis_names[uid]:
                        continue

                    self._configure_1d_tab(uid, stream_name, detector_name, 0)

            if self._plots.widget(1).isVisible():
                for detector_name in sorted(signals):
                    if detector_name not in self._2d_z_axis_names[uid]:
                        continue

                    self._configure_2d_scatter_tab(uid, stream_name, detector_name, 1)

            if self._plots.widget(2).isVisible():
                for detector_name in sorted(signals):
                    if detector_name not in self._2d_z_axis_names[uid]:
                        continue

                    self._configure_2d_grid_tab(uid, stream_name, detector_name, 2)

    def _configure_1d_tab(
        self, uid: str, stream_name: str, detector_name: str, tab_index: int
    ):
        x_axis_signal = self._1d_x_axis_names[uid]
        x_axis_data = self._data_aggregator.get_data(uid, x_axis_signal)
        if x_axis_data is None:
            return
        cached_data = self._data_aggregator.get_data(uid, detector_name)

        # NOTE: Shorthand format for a static baseline
        if isinstance(cached_data, (int, float)):
            cached_data = np.full_like(x_axis_data, cached_data)

        if len(cached_data.shape) > 1:
            cached_data = np.trim_zeros(np.nan_to_num(cached_data.flatten()))

        plot_widget = self._plots.widget(tab_index)
        plot_widget.getXAxis().setLabel(
            self._data_aggregator.get_signal_name(uid, x_axis_signal)
        )
        plot_widget.addCurve(
            x_axis_data,
            cached_data,
            ylabel=self._data_aggregator.get_signal_name(uid, detector_name),
            legend=detector_name + " - " + stream_name + "   (" + uid + ")",
        )

    def _configure_2d_scatter_tab(
        self, uid: str, stream_name: str, detector_name: str, tab_index: int
    ):
        x_axis_signal = self._2d_x_axis_names[uid]
        y_axis_signal = self._2d_y_axis_names[uid]
        if x_axis_signal == "" or y_axis_signal == "":
            return

        x_axis_data = self._data_aggregator.get_data(uid, x_axis_signal)
        y_axis_data = self._data_aggregator.get_data(uid, y_axis_signal)
        cached_data = self._data_aggregator.get_data(uid, detector_name)

        if len(cached_data.shape) > 1:
            cached_data = np.trim_zeros(np.nan_to_num(cached_data.flatten()))

        plot_widget = self._plots.widget(tab_index)
        plot_widget.getXAxis().setLabel(
            self._data_aggregator.get_signal_name(uid, x_axis_signal)
        )
        plot_widget.getYAxis().setLabel(
            self._data_aggregator.get_signal_name(uid, y_axis_signal)
        )
        plot_widget.addScatter(
            x_axis_data,
            y_axis_data,
            cached_data,
            legend=detector_name + " - " + stream_name + " - " + uid,
        )
        plot_widget.resetZoom()

    def _configure_2d_grid_tab(
        self, uid: str, stream_name: str, detector_name: str, tab_index: int
    ):
        x_axis_signal = self._2d_x_axis_names[uid]
        y_axis_signal = self._2d_y_axis_names[uid]
        if x_axis_signal == "" or y_axis_signal == "":
            return

        cached_data = self._data_aggregator.get_data(uid, detector_name)
        _metadata = self._data_aggregator.get_metadata(uid)

        shape = tuple(_metadata.get("shape", (0, 0)))
        extents = _metadata.get("extents", ((0, 0), (0, 0)))
        scale = (
            (extents[1][1] - extents[1][0]) / (shape[1] - 1),
            (extents[0][1] - extents[0][0]) / (shape[0] - 1),
        )
        origin = (extents[1][0] - scale[0] / 2, extents[0][0] - scale[1] / 2)

        # Probably trying to plot 1D data in a 2D plot
        if cached_data.shape != shape:
            return

        plot_widget = self._plots.widget(tab_index)
        plot_widget.getXAxis().setLabel(
            self._data_aggregator.get_signal_name(uid, x_axis_signal)
        )
        plot_widget.getYAxis().setLabel(
            self._data_aggregator.get_signal_name(uid, y_axis_signal)
        )
        plot_widget.addImage(
            cached_data,
            origin=origin,
            scale=scale,
            legend=detector_name + " - " + stream_name + " - " + uid,
            resetzoom=True,
        )

    def _on_plot_tab_changed(self, new_index: int):
        self.plot_tab_changed.emit(self._plots.tabText(new_index))

        self.update_plots()

    def _on_1d_signals_changed(self, x_signal: str, y_signals: set[str]):
        for uid, _ in self._current_uids:
            self._1d_x_axis_names[uid] = x_signal
            self._1d_y_axis_names[uid] = y_signals

        self.update_plots()

    def _on_2d_signals_changed(self, x_signal: str, y_signal: str, z_signals: set[str]):
        for uid, _ in self._current_uids:
            self._2d_x_axis_names[uid] = x_signal
            self._2d_y_axis_names[uid] = y_signal
            self._2d_z_axis_names[uid] = z_signals

        self.update_plots()

    def _on_custom_signal_added(self, uid: str, name: str, expression: str):
        self._data_aggregator.add_custom_signal(uid, name, expression)
        self.update_plots()
