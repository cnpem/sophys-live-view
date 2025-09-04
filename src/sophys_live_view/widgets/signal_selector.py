from collections import defaultdict

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QButtonGroup,
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
    selected_signals_changed_1d = Signal(str, set)  # X, Y
    selected_signals_changed_2d = Signal(str, str, set)  # X, Y, Z

    def __init__(self, data_source_manager, change_stream_signal: Signal):
        super().__init__()

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
        self._1d_signal_selection_table.selected_signals_changed.connect(
            self.selected_signals_changed_1d.emit
        )
        self._signal_selection_stack.addWidget(self._1d_signal_selection_table)

        self._2d_signal_selection_table = SelectionTable2D(self)
        self._2d_signal_selection_table.selected_signals_changed.connect(
            self.selected_signals_changed_2d.emit
        )
        self._signal_selection_stack.addWidget(self._2d_signal_selection_table)

        data_source_manager.new_data_stream.connect(self._add_new_signal)
        change_stream_signal.connect(self.change_current_streams)

    def set_plot_tab_changed_signal(self, signal: Signal):
        signal.connect(self._change_tab)

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
        self._2d_signal_selection_table.configure_signals(new_uids, new_signals)

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
        name_to_index = {"1D": 0, "2D - Scatter": 1, "2D - Grid": 1}
        self._signal_selection_stack.setCurrentIndex(name_to_index[new_tab_name])


class SelectionTable1D(QTableWidget):
    selected_signals_changed = Signal(str, set)  # X, Y

    def __init__(self, parent):
        super().__init__(parent)

        self._parent = parent

        self._selected_x_signal = ""
        self._selected_y_signals = set()

        self.setColumnCount(3)
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

            item = QTableWidgetItem(signal)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
            )
            self.setItem(index, 0, item)

            x_axis_radio_button = QRadioButton()
            x_axis_radio_button.setStyleSheet("margin-left:50%; margin-right:50%;")
            x_axis_radio_button.clicked.connect(self._change_x_axis_signal)
            self.setCellWidget(index, 1, x_axis_radio_button)

            y_axis_checkbox = QCheckBox()
            y_axis_checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
            y_axis_checkbox.toggled.connect(self._change_y_axis_signal)
            self.setCellWidget(index, 2, y_axis_checkbox)

        self._change_x_axis_signal()
        self._change_y_axis_signal()

    def _change_x_axis_signal(self):
        self._selected_x_signal = self._get_selected_x_axis_signal()

        self.selected_signals_changed.emit(
            self._selected_x_signal, self._selected_y_signals
        )

    def _change_y_axis_signal(self):
        self._selected_y_signals = self._get_selected_y_axis_signals()

        self.selected_signals_changed.emit(
            self._selected_x_signal, self._selected_y_signals
        )

    def _get_selected_x_axis_signal(self):
        selected_signal = ""

        for index in range(self.rowCount()):
            if self.cellWidget(index, 1).isChecked():
                signal = self.item(index, 0).text()
                selected_signal = signal
                continue

        if selected_signal == "":
            for index in range(self.rowCount()):
                signal = self.item(index, 0).text()
                if signal in self._parent.default_independent_signals:
                    selected_signal = signal

                    self.cellWidget(index, 1).setChecked(True)
                    break

        return selected_signal

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
    selected_signals_changed = Signal(str, str, set)  # X, Y, Z

    def __init__(self, parent):
        super().__init__(parent)

        self._parent = parent

        self._selected_x_signal = ""
        self._selected_y_signal = ""
        self._selected_z_signals = set()

        self._x_buttons_container = QButtonGroup()
        self._y_buttons_container = QButtonGroup()

        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Signal", "X", "Y", "Data"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )

    def configure_signals(self, uids, signals):
        self.setRowCount(0)

        sorted_signals_list = sorted(signals)
        for index, signal in enumerate(sorted_signals_list):
            self.insertRow(index)

            item = QTableWidgetItem(signal)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
            )
            self.setItem(index, 0, item)

            x_axis_radio_button = QRadioButton()
            x_axis_radio_button.setStyleSheet("margin-left:50%; margin-right:50%;")
            x_axis_radio_button.clicked.connect(self._change_x_axis_signal)
            self._x_buttons_container.addButton(x_axis_radio_button)
            self.setCellWidget(index, 1, x_axis_radio_button)

            y_axis_radio_button = QRadioButton()
            y_axis_radio_button.setStyleSheet("margin-left:50%; margin-right:50%;")
            y_axis_radio_button.clicked.connect(self._change_y_axis_signal)
            self._y_buttons_container.addButton(y_axis_radio_button)
            self.setCellWidget(index, 2, y_axis_radio_button)

            z_axis_checkbox = QCheckBox()
            z_axis_checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
            z_axis_checkbox.toggled.connect(self._change_z_axis_signals)
            self.setCellWidget(index, 3, z_axis_checkbox)

        self._change_x_axis_signal()
        self._change_y_axis_signal()
        self._change_z_axis_signals()

    def _get_selected_x_axis_signal(self):
        selected_signal = ""

        for index in range(self.rowCount()):
            if self.cellWidget(index, 1).isChecked():
                signal = self.item(index, 0).text()
                selected_signal = signal
                continue

        if selected_signal == "" and len(self._parent.default_independent_signals) >= 2:
            for index in range(self.rowCount()):
                signal = self.item(index, 0).text()
                if signal == self._parent.default_independent_signals[0]:
                    selected_signal = signal

                    self.cellWidget(index, 1).setChecked(True)
                    break

        return selected_signal

    def _get_selected_y_axis_signal(self):
        selected_signal = ""

        for index in range(self.rowCount()):
            if self.cellWidget(index, 2).isChecked():
                signal = self.item(index, 0).text()
                selected_signal = signal
                continue

        if selected_signal == "" and len(self._parent.default_independent_signals) >= 2:
            for index in range(self.rowCount()):
                signal = self.item(index, 0).text()
                if signal == self._parent.default_independent_signals[1]:
                    selected_signal = signal

                    self.cellWidget(index, 2).setChecked(True)
                    break

        return selected_signal

    def _get_selected_z_axis_signals(self):
        selected_signals = set()

        for index in range(self.rowCount()):
            if self.cellWidget(index, 3).isChecked():
                selected_signals.add(self.item(index, 0).text())

        if len(selected_signals) == 0:
            for index in range(self.rowCount()):
                if self.item(index, 0).text() in self._parent.default_dependent_signals:
                    self.cellWidget(index, 3).setChecked(True)
                    selected_signals.add(self.item(index, 0).text())

        return selected_signals

    def _change_x_axis_signal(self):
        self._selected_x_signal = self._get_selected_x_axis_signal()

        self.selected_signals_changed.emit(
            self._selected_x_signal, self._selected_y_signal, self._selected_z_signals
        )

    def _change_y_axis_signal(self):
        self._selected_y_signal = self._get_selected_y_axis_signal()

        self.selected_signals_changed.emit(
            self._selected_x_signal, self._selected_y_signal, self._selected_z_signals
        )

    def _change_z_axis_signals(self):
        self._selected_z_signals = self._get_selected_z_axis_signals()

        self.selected_signals_changed.emit(
            self._selected_x_signal, self._selected_y_signal, self._selected_z_signals
        )
