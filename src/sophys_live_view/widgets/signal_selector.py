from abc import abstractmethod
from collections import defaultdict
from functools import partial

from qtpy.QtWidgets import (
    QCheckBox,
    QHeaderView,
    QRadioButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SignalSelector(QWidget):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._parent = parent

        self._signals = dict()
        self.uids_with_signal = defaultdict(lambda: set())

        self.default_dependent_signals = set()
        self.default_independent_signals = list()
        self._default_dependent_signals = dict()
        self._default_independent_signals = dict()

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._signal_selection_stack = QStackedWidget()
        layout.addWidget(self._signal_selection_stack)

        self._1d_signal_selection_table = SelectionTable1D(self)
        self._signal_selection_stack.addWidget(self._1d_signal_selection_table)

        self._2d_scatter_signal_selection_table = SelectionTable2DScatter(self)
        self._signal_selection_stack.addWidget(self._2d_scatter_signal_selection_table)

        self._2d_grid_signal_selection_table = SelectionTable2DGrid(self)
        self._signal_selection_stack.addWidget(self._2d_grid_signal_selection_table)

        self._parent.data_source_manager.new_data_stream.connect(self._add_new_signal)
        self.plot_display.plot_tab_changed.connect(self._change_tab)

    def change_current_streams(self, new_uids_and_names: list[tuple[str, str]]):
        new_signals = set()
        new_uids = set()
        for uid, _ in new_uids_and_names:
            new_signals |= self._signals[uid]
            new_uids.add(uid)

        if len(new_uids) == 1:
            self.default_independent_signals = self._default_independent_signals.get(
                list(new_uids)[0], set()
            )
            self.default_dependent_signals = self._default_dependent_signals.get(
                list(new_uids)[0], set()
            )
        else:
            self.default_independent_signals = list()
            self.default_dependent_signals = set()

            for uid in new_uids:
                self.default_independent_signals.extend(
                    self._default_independent_signals.get(uid, [])
                )
                self.default_dependent_signals |= self._default_dependent_signals.get(
                    uid, set()
                )

        self._1d_signal_selection_table.configure_signals(new_uids, new_signals)
        self._2d_scatter_signal_selection_table.configure_signals(new_uids, new_signals)
        self._2d_grid_signal_selection_table.configure_signals(new_uids, new_signals)

    def _add_new_signal(
        self,
        uid: str,
        subuid: str,
        display_name: str,
        signals: set[str],
        detectors: set[str],
        motors: list[str],
        metadata: dict,
    ):
        self._signals[subuid] = signals

        self._default_dependent_signals[subuid] = detectors
        self._default_independent_signals[subuid] = motors

        for signal in signals:
            self.uids_with_signal[signal].add(subuid)

    def _change_tab(self, new_tab_name: str):
        name_to_index = {"1D": 0, "2D - Scatter": 1, "2D - Grid": 2}
        self._signal_selection_stack.setCurrentIndex(name_to_index[new_tab_name])

    @property
    def plot_display(self):
        return self._parent.plot_display


class SelectionTable1D(QTableWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self._parent = parent
        self._old_uids = set()

        self.insertColumn(0)
        self.insertColumn(0)
        self.insertColumn(0)
        self.setHorizontalHeaderLabels(["Signal", "X", "Y"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )

    def configure_signals(self, uids, signals):
        self.setRowCount(0)

        sorted_signals_list = sorted(signals)
        for index, signal in enumerate(sorted_signals_list):
            self.insertRow(index)
            self.setItem(index, 0, QTableWidgetItem(signal))

            x_axis_radio_button = QRadioButton()
            x_axis_radio_button.setStyleSheet("margin-left:50%; margin-right:50%;")
            x_axis_radio_button.clicked.connect(
                partial(self._change_x_axis_signal, signal)
            )
            self.setCellWidget(index, 1, x_axis_radio_button)

            y_axis_checkbox = QCheckBox()
            y_axis_checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
            y_axis_checkbox.toggled.connect(self._change_y_axis_signal)
            self.setCellWidget(index, 2, y_axis_checkbox)

            if signal in self._parent.default_independent_signals:
                self._change_x_axis_signal(signal)

        self._change_y_axis_signal()

    def _change_x_axis_signal(self, new_signal_name: str):
        self._clear_x_axis_buttons(new_signal_name)

        for uid in self._parent.uids_with_signal[new_signal_name]:
            self._parent.plot_display.configure_1d_x_axis_name(uid, new_signal_name)
        self._parent.plot_display.update_plots()

    def _change_y_axis_signal(self):
        selected_signals = self._get_selected_y_axis_signals()

        uids = self._old_uids
        for signal in selected_signals:
            uids |= self._parent.uids_with_signal[signal]

        for uid in uids:
            self._parent.plot_display.configure_1d_y_axis_names(uid, selected_signals)
        self._parent.plot_display.update_plots()

        self._old_uids = uids

    def _clear_x_axis_buttons(self, selected_signal: str):
        for index in range(self.rowCount()):
            if self.item(index, 0).text() == selected_signal:
                self.cellWidget(index, 1).setChecked(True)
                continue

            self.cellWidget(index, 1).setChecked(False)

    def _get_selected_y_axis_signals(self):
        selected_signals = set()

        for index in range(self.rowCount()):
            if self.cellWidget(index, 2).isChecked():
                selected_signals.add(self.item(index, 0).text())

        if len(selected_signals) == 0:
            for index in range(self.rowCount()):
                if self.item(index, 0).text() in self._parent.default_dependent_signals:
                    self.cellWidget(index, 2).setChecked(True)
                    selected_signals.add(self.item(index, 0).text())

        return selected_signals


class SelectionTable2D(QTableWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self._parent = parent
        self._old_x_uids = set()
        self._old_y_uids = set()

        self.insertColumn(0)
        self.insertColumn(0)
        self.insertColumn(0)
        self.setHorizontalHeaderLabels(["Signal", "Independent", "Dependent"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )

    def configure_signals(self, uids, signals):
        self.setRowCount(0)

        sorted_signals_list = sorted(signals)
        for index, signal in enumerate(sorted_signals_list):
            self.insertRow(index)
            self.setItem(index, 0, QTableWidgetItem(signal))

            x_axis_checkbox = QCheckBox()
            x_axis_checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
            x_axis_checkbox.toggled.connect(self._change_x_axis_signal)
            self.setCellWidget(index, 1, x_axis_checkbox)

            y_axis_checkbox = QCheckBox()
            y_axis_checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
            y_axis_checkbox.toggled.connect(self._change_y_axis_signal)
            self.setCellWidget(index, 2, y_axis_checkbox)

        self._change_x_axis_signal()
        self._change_y_axis_signal()

    def _get_selected_x_axis_signals(self):
        selected_signals = set()

        for index in range(self.rowCount()):
            if self.cellWidget(index, 1).isChecked():
                selected_signals.add(self.item(index, 0).text())

        if len(selected_signals) == 0:
            for index in range(self.rowCount()):
                if (
                    self.item(index, 0).text()
                    in self._parent.default_independent_signals
                ):
                    self.cellWidget(index, 1).setChecked(True)
                    selected_signals.add(self.item(index, 0).text())

        return selected_signals

    def _get_selected_y_axis_signals(self):
        selected_signals = set()

        for index in range(self.rowCount()):
            if self.cellWidget(index, 2).isChecked():
                selected_signals.add(self.item(index, 0).text())

        if len(selected_signals) == 0:
            for index in range(self.rowCount()):
                if self.item(index, 0).text() in self._parent.default_dependent_signals:
                    self.cellWidget(index, 2).setChecked(True)
                    selected_signals.add(self.item(index, 0).text())

        return selected_signals

    @abstractmethod
    def _change_x_axis_signal(self):
        pass

    @abstractmethod
    def _change_y_axis_signal(self):
        pass


class SelectionTable2DScatter(SelectionTable2D):
    def _change_x_axis_signal(self):
        selected_signals = self._get_selected_x_axis_signals()

        uids = self._old_x_uids
        for signal in selected_signals:
            uids |= self._parent.uids_with_signal[signal]

        for uid in uids:
            self._parent.plot_display.configure_2d_scatter_x_axis_names(
                uid, selected_signals
            )
        self._parent.plot_display.update_plots()

        self._old_x_uids = uids

    def _change_y_axis_signal(self):
        selected_signals = self._get_selected_y_axis_signals()

        uids = self._old_y_uids
        for signal in selected_signals:
            uids |= self._parent.uids_with_signal[signal]

        for uid in uids:
            self._parent.plot_display.configure_2d_scatter_y_axis_names(
                uid, selected_signals
            )
        self._parent.plot_display.update_plots()

        self._old_y_uids = uids


class SelectionTable2DGrid(SelectionTable2D):
    def _change_x_axis_signal(self):
        selected_signals = self._get_selected_x_axis_signals()

        uids = self._old_x_uids
        for signal in selected_signals:
            uids |= self._parent.uids_with_signal[signal]

        for uid in uids:
            self._parent.plot_display.configure_2d_grid_x_axis_names(
                uid, selected_signals
            )
        self._parent.plot_display.update_plots()

        self._old_x_uids = uids

    def _change_y_axis_signal(self):
        selected_signals = self._get_selected_y_axis_signals()

        uids = self._old_y_uids
        for signal in selected_signals:
            uids |= self._parent.uids_with_signal[signal]

        for uid in uids:
            self._parent.plot_display.configure_2d_grid_y_axis_names(
                uid, selected_signals
            )
        self._parent.plot_display.update_plots()

        self._old_y_uids = uids
