from collections import defaultdict
from functools import partial

from qtpy.QtWidgets import (
    QCheckBox,
    QHeaderView,
    QRadioButton,
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
        self._uids_with_signal = defaultdict(lambda: set())

        self._old_y_axis_signals = set()

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._signal_selection_table = QTableWidget()
        layout.addWidget(self._signal_selection_table)

        self._signal_selection_table.insertColumn(0)
        self._signal_selection_table.insertColumn(0)
        self._signal_selection_table.insertColumn(0)
        self._signal_selection_table.setHorizontalHeaderLabels(["Signal", "X", "Y"])
        self._signal_selection_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._signal_selection_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._signal_selection_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )

        self._parent.data_source_manager.new_data_stream.connect(self._add_new_signal)

    def change_current_streams(self, new_uids_and_names: list[tuple[str, str]]):
        new_signals = set()
        new_uids = set()
        for uid, _ in new_uids_and_names:
            new_signals |= self._signals[uid]
            new_uids.add(uid)

        self._configure_signals(new_uids, new_signals)

    def _configure_signals(self, uids, signals):
        self._signal_selection_table.setRowCount(0)

        previous_x_axis_signals = set(
            self._parent.plot_display.get_1d_x_axis_name(uid) for uid in uids
        )
        previous_y_axis_signals = self._old_y_axis_signals

        sorted_signals_list = sorted(signals)
        for index, signal in enumerate(sorted_signals_list):
            self._signal_selection_table.insertRow(index)
            self._signal_selection_table.setItem(index, 0, QTableWidgetItem(signal))

            x_axis_checkbox = QRadioButton()
            x_axis_checkbox.clicked.connect(partial(self._change_x_axis_signal, signal))
            self._signal_selection_table.setCellWidget(index, 1, x_axis_checkbox)
            if signal in previous_x_axis_signals:
                x_axis_checkbox.setChecked(True)

            y_axis_checkbox = QCheckBox()
            y_axis_checkbox.toggled.connect(self._change_y_axis_signal)
            self._signal_selection_table.setCellWidget(index, 2, y_axis_checkbox)
            if signal in previous_y_axis_signals:
                y_axis_checkbox.setChecked(True)
            self._change_y_axis_signal()

    def _change_x_axis_signal(self, new_signal_name: str):
        self._clear_x_axis_buttons(new_signal_name)

        for uid in self._uids_with_signal[new_signal_name]:
            self._parent.plot_display.configure_1d_x_axis_name(uid, new_signal_name)
        self._parent.plot_display.update_plots()

    def _change_y_axis_signal(self):
        selected_signals = self._get_selected_y_axis_signals()

        uids = set()
        for signal in selected_signals | self._old_y_axis_signals:
            uids |= self._uids_with_signal[signal]

        for uid in uids:
            self._parent.plot_display.configure_1d_y_axis_names(uid, selected_signals)
        self._parent.plot_display.update_plots()

        self._old_y_axis_signals = selected_signals

    def _add_new_signal(
        self,
        uid: str,
        subuid: str,
        display_name: str,
        signals: set[str],
        metadata: dict,
    ):
        self._signals[subuid] = signals

        for signal in signals:
            self._uids_with_signal[signal].add(subuid)

    def _clear_x_axis_buttons(self, selected_signal: str):
        for index in range(self._signal_selection_table.rowCount()):
            if self._signal_selection_table.item(index, 0).text() == selected_signal:
                continue

            self._signal_selection_table.cellWidget(index, 1).setChecked(False)

    def _get_selected_y_axis_signals(self):
        selected_signals = set()
        x_axis_index = -1

        for index in range(self._signal_selection_table.rowCount()):
            if self._signal_selection_table.cellWidget(index, 2).isChecked():
                selected_signals.add(self._signal_selection_table.item(index, 0).text())
            if self._signal_selection_table.cellWidget(index, 1).isChecked():
                x_axis_index = index

        if len(selected_signals) == 0 and self._signal_selection_table.rowCount() >= 2:
            if x_axis_index == 0:
                self._signal_selection_table.cellWidget(1, 2).setChecked(True)
                selected_signals.add(self._signal_selection_table.item(1, 0).text())
            else:
                self._signal_selection_table.cellWidget(0, 2).setChecked(True)
                selected_signals.add(self._signal_selection_table.item(0, 0).text())

        return selected_signals
