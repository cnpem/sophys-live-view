from collections import defaultdict

import numpy as np
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QStackedWidget, QTabWidget
from silx.gui.colors import Colormap
from silx.gui.plot.PlotWindow import Plot1D, Plot2D


class PlotDisplay(QStackedWidget):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._parent = parent

        self._current_uids = [("", "")]
        self._data_cache = defaultdict(lambda: defaultdict(lambda: np.array([[], []])))

        self._1d_x_axis_names = defaultdict(lambda: "timestamp")
        self._1d_y_axis_names = defaultdict(lambda: set())

        self._2d_scatter_x_axis_names = defaultdict(lambda: set())
        self._2d_scatter_y_axis_names = defaultdict(lambda: set())

        standby_label = QLabel("Waiting for a run to be selected...")
        standby_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
        )
        self.addWidget(standby_label)

        self._plots = QTabWidget()
        _plot_1d = Plot1D()
        self._plots.addTab(_plot_1d, "1D")
        _plot_2d_scatter = Plot2D()
        _plot_2d_scatter.setDefaultColormap(Colormap(name="viridis"))
        self._plots.addTab(_plot_2d_scatter, "2D - Scatter")
        self.addWidget(self._plots)

        self._parent.data_source_manager.new_data_received.connect(
            self._receive_new_data
        )

    def update_plots(self):
        self.change_current_streams(self._current_uids)

    def change_current_streams(self, new_uids_and_names: list[tuple[str, str]]):
        self._current_uids = new_uids_and_names

        if len(new_uids_and_names) == 1 and new_uids_and_names[0][0] == "":
            self.setCurrentIndex(0)
            return

        self._plots.widget(0).clear()
        self._plots.widget(1).clear()

        for uid, _ in new_uids_and_names:
            self.setCurrentWidget(self._plots)

            for detector_name in self._data_cache[uid]:
                if detector_name not in self._1d_y_axis_names[uid]:
                    continue

                self._configure_1d_tab(uid, detector_name, 0)

            for detector_name in self._data_cache[uid]:
                if detector_name not in self._2d_scatter_y_axis_names[uid]:
                    continue

                self._configure_2d_scatter_tab(uid, detector_name, 1)

    def get_1d_x_axis_name(self, uid: str):
        return self._1d_x_axis_names[uid]

    def configure_1d_x_axis_name(self, uid: str, x_axis_name: str):
        self._1d_x_axis_names[uid] = x_axis_name

    def get_1d_y_axis_names(self, uid: str):
        return self._1d_y_axis_names[uid]

    def configure_1d_y_axis_names(self, uid: str, y_axis_names: set[str]):
        self._1d_y_axis_names[uid] = y_axis_names

    def get_2d_scatter_x_axis_names(self, uid: str):
        return self._2d_scatter_x_axis_names[uid]

    def configure_2d_scatter_x_axis_names(self, uid: str, x_axis_name: str):
        self._2d_scatter_x_axis_names[uid] = x_axis_name

    def get_2d_scatter_y_axis_names(self, uid: str):
        return self._2d_scatter_y_axis_names[uid]

    def configure_2d_scatter_y_axis_names(self, uid: str, y_axis_names: set[str]):
        self._2d_scatter_y_axis_names[uid] = y_axis_names

    def _receive_new_data(self, uid: str, subuid: str, new_data):
        for detector_name, detector_values in new_data.items():
            self._data_cache[subuid][detector_name] = np.append(
                self._data_cache[subuid][detector_name], detector_values
            )
        self.update_plots()

    def _configure_1d_tab(self, uid: str, detector_name: str, tab_index: int):
        x_axis_data = self._data_cache[uid][self._1d_x_axis_names[uid]]
        cached_data = self._data_cache[uid][detector_name]

        plot_widget = self._plots.widget(tab_index)
        plot_widget.addCurve(x_axis_data, cached_data, legend=uid + detector_name)

    def _configure_2d_scatter_tab(self, uid: str, detector_name: str, tab_index: int):
        independent_axis_fields = list(self._2d_scatter_x_axis_names[uid])
        if len(independent_axis_fields) < 2:
            return

        x_axis_data = self._data_cache[uid][independent_axis_fields[0]]
        y_axis_data = self._data_cache[uid][independent_axis_fields[1]]
        cached_data = self._data_cache[uid][detector_name]

        plot_widget = self._plots.widget(tab_index)
        plot_widget.addScatter(
            x_axis_data, y_axis_data, cached_data, legend=uid + detector_name
        )
