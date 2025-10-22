from collections import defaultdict

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .interfaces import CUSTOM_SIGNALS_ENVIRONMENT, ISignalSelector


class SignalSelector(ISignalSelector):
    def __init__(self, data_source_manager, selected_streams_changed: Signal):
        super().__init__()

        self._current_uids = set()

        self._signals = dict()
        self._signals_name_map = dict()
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
        self._1d_signal_selection_table.selected_streams_changed.connect(
            self.selected_signals_changed_1d.emit
        )
        self._signal_selection_stack.addWidget(self._1d_signal_selection_table)

        self._2d_signal_selection_table = SelectionTable2D(self)
        self._2d_signal_selection_table.selected_streams_changed.connect(
            self.selected_signals_changed_2d.emit
        )
        self._signal_selection_stack.addWidget(self._2d_signal_selection_table)

        self._custom_signal_button = QPushButton("Add custom signal...")
        self._custom_signal_button.setVisible(False)
        self._custom_signal_button.clicked.connect(self._custom_signal_button_clicked)
        layout.addWidget(self._custom_signal_button)

        data_source_manager.new_data_stream.connect(self._add_new_signal)
        selected_streams_changed.connect(self.change_current_streams)

    def set_plot_tab_changed_signal(self, signal: Signal):
        signal.connect(self._change_tab)

    def change_current_streams(self, new_uids_and_names: list[tuple[str, str]]):
        new_signals = set()
        new_uids = set()
        for uid, _ in new_uids_and_names:
            new_signals |= self._signals[uid]
            new_uids.add(uid)

        self._current_uids = new_uids
        self._custom_signal_button.setVisible(len(new_uids) == 1)

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

    def reload(self):
        self.change_current_streams([(i, None) for i in self._current_uids])

    def get_signal_name(self, signal: str):
        # FIXME: Properly handle different names in each uid
        name = signal
        for uid in self.uids_with_signal[signal]:
            name = self._signals_name_map[uid].get(signal, signal)
        return name

    def _add_new_signal(
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
        self._signals[subuid] = signals
        self._signals_name_map[subuid] = signals_name_map

        self._default_dependent_signals[subuid] = detectors
        self._default_independent_signals[subuid] = motors

        for signal in signals:
            self.uids_with_signal[signal].add(subuid)

    def _add_custom_signal(self, uid: str, signal_name: str, signal_expression: str):
        self._signals[uid].add(signal_name)
        self._signals_name_map[uid][signal_name] = signal_name + " (custom)"
        self.uids_with_signal[signal_name].add(uid)

        self.custom_signal_added.emit(uid, signal_name, signal_expression)

        self.reload()

    def _change_tab(self, new_tab_name: str):
        name_to_index = {"1D": 0, "2D - Scatter": 1, "2D - Grid": 1}
        self._signal_selection_stack.setCurrentIndex(name_to_index[new_tab_name])

    def _custom_signal_button_clicked(self):
        uid = list(self._current_uids)[0]
        signals = {k: self.get_signal_name(k) for k in self._signals[uid]}

        dialog = QDialog()
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        custom_signal_selector = CustomSignalCreator(uid, signals)
        layout.addWidget(custom_signal_selector)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Help
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        button_box.helpRequested.connect(custom_signal_selector.toggle_help)
        layout.addWidget(button_box)

        dialog.setFixedSize(450, 500)

        if dialog.exec() == QDialog.DialogCode.Rejected:
            return

        name, expr = custom_signal_selector.get_custom_signal_parameters()
        valid, exception = custom_signal_selector.validate_expression(expr)
        if valid:
            self._add_custom_signal(uid, name, expr)
        else:
            QMessageBox.critical(
                self,
                "Invalid expression!",
                f"The inputted expression is invalid: \n{exception}",
            )


class SelectionTable1D(QTableWidget):
    selected_streams_changed = Signal(str, set)  # X, Y

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

            signal_name = self._parent.get_signal_name(signal)
            item = QTableWidgetItem(signal_name)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
            )
            if "(custom)" in signal_name:
                _f = item.font()
                _f.setItalic(True)
                item.setFont(_f)
            item.setData(Qt.ItemDataRole.UserRole, signal)
            item.setFlags(~Qt.ItemFlag.ItemIsEditable)
            self.setItem(index, 0, item)

            x_axis_radio_button = QRadioButton()
            x_axis_radio_button.setStyleSheet("margin-left:50%; margin-right:50%;")
            x_axis_radio_button.clicked.connect(self._change_x_axis_signal)
            self.setCellWidget(index, 1, x_axis_radio_button)

            y_axis_checkbox = QCheckBox()
            y_axis_checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
            y_axis_checkbox.toggled.connect(self._change_y_axis_signal)
            self.setCellWidget(index, 2, y_axis_checkbox)

        # NOTE: Avoid sending essentially the same signal twice in a row.
        self.blockSignals(True)
        self._change_x_axis_signal()
        self.blockSignals(False)
        self._change_y_axis_signal()

    def _change_x_axis_signal(self):
        self._selected_x_signal = self._get_selected_x_axis_signal()

        self.selected_streams_changed.emit(
            self._selected_x_signal, self._selected_y_signals
        )

    def _change_y_axis_signal(self):
        self._selected_y_signals = self._get_selected_y_axis_signals()

        self.selected_streams_changed.emit(
            self._selected_x_signal, self._selected_y_signals
        )

    def _get_selected_x_axis_signal(self):
        selected_signal = ""

        for index in range(self.rowCount()):
            if self.cellWidget(index, 1).isChecked():
                signal = self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                selected_signal = signal
                continue

        if selected_signal == "":
            for index in range(self.rowCount()):
                signal = self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                if signal in self._parent.default_independent_signals:
                    selected_signal = signal

                    self.cellWidget(index, 1).setChecked(True)
                    break

        return selected_signal

    def _get_selected_y_axis_signals(self):
        selected_signals = set()

        for index in range(self.rowCount()):
            if self.cellWidget(index, 2).isChecked():
                selected_signals.add(self.item(index, 0).data(Qt.ItemDataRole.UserRole))

        if len(selected_signals) == 0:
            for index in range(self.rowCount()):
                if (
                    self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                    in self._parent.default_dependent_signals
                ):
                    self.cellWidget(index, 2).setChecked(True)
                    selected_signals.add(
                        self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                    )

        return selected_signals


class SelectionTable2D(QTableWidget):
    selected_streams_changed = Signal(str, str, set)  # X, Y, Z

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

            signal_name = self._parent.get_signal_name(signal)
            item = QTableWidgetItem(signal_name)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
            )
            if "(custom)" in signal_name:
                _f = item.font()
                _f.setItalic(True)
                item.setFont(_f)
            item.setData(Qt.ItemDataRole.UserRole, signal)
            item.setFlags(~Qt.ItemFlag.ItemIsEditable)
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
                signal = self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                selected_signal = signal
                continue

        if selected_signal == "" and len(self._parent.default_independent_signals) >= 2:
            for index in range(self.rowCount()):
                signal = self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                if signal == self._parent.default_independent_signals[1]:
                    selected_signal = signal

                    self.cellWidget(index, 1).setChecked(True)
                    break

        return selected_signal

    def _get_selected_y_axis_signal(self):
        selected_signal = ""

        for index in range(self.rowCount()):
            if self.cellWidget(index, 2).isChecked():
                signal = self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                selected_signal = signal
                continue

        if selected_signal == "" and len(self._parent.default_independent_signals) >= 2:
            for index in range(self.rowCount()):
                signal = self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                if signal == self._parent.default_independent_signals[0]:
                    selected_signal = signal

                    self.cellWidget(index, 2).setChecked(True)
                    break

        return selected_signal

    def _get_selected_z_axis_signals(self):
        selected_signals = set()

        for index in range(self.rowCount()):
            if self.cellWidget(index, 3).isChecked():
                selected_signals.add(self.item(index, 0).data(Qt.ItemDataRole.UserRole))

        if len(selected_signals) == 0:
            for index in range(self.rowCount()):
                if (
                    self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                    in self._parent.default_dependent_signals
                ):
                    self.cellWidget(index, 3).setChecked(True)
                    selected_signals.add(
                        self.item(index, 0).data(Qt.ItemDataRole.UserRole)
                    )

        return selected_signals

    def _change_x_axis_signal(self):
        self._selected_x_signal = self._get_selected_x_axis_signal()

        self.selected_streams_changed.emit(
            self._selected_x_signal, self._selected_y_signal, self._selected_z_signals
        )

    def _change_y_axis_signal(self):
        self._selected_y_signal = self._get_selected_y_axis_signal()

        self.selected_streams_changed.emit(
            self._selected_x_signal, self._selected_y_signal, self._selected_z_signals
        )

    def _change_z_axis_signals(self):
        self._selected_z_signals = self._get_selected_z_axis_signals()

        self.selected_streams_changed.emit(
            self._selected_x_signal, self._selected_y_signal, self._selected_z_signals
        )


class CustomSignalCreator(QStackedWidget):
    def __init__(self, run_uid: str, signals: dict[str, str]):
        super().__init__()

        self._run_uid = run_uid
        self._expr_signal_names = list(signals.keys())

        main = QWidget()
        layout = QVBoxLayout()
        main.setLayout(layout)
        self.addWidget(main)

        _w = QTableWidget(columnCount=2)
        _w.setHorizontalHeaderLabels(["Display name", "Name inside the expression"])
        _w.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        _w.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        _w.verticalHeader().setVisible(False)

        for signal in sorted(signals.keys()):
            row_index = _w.rowCount()
            _w.insertRow(row_index)

            _w.setItem(row_index, 0, QTableWidgetItem(signals[signal]))
            _w.setItem(row_index, 1, QTableWidgetItem(signal))

        layout.addWidget(_w)

        _w = QFrame()
        _l = QGridLayout()
        _l.addWidget(QLabel("Signal name"), 0, 0, 1, 1)
        self.signal_name_line = QLineEdit("test")
        _l.addWidget(self.signal_name_line, 0, 1, 1, 1)
        _l.addWidget(QLabel("Expression"), 1, 0, 1, 1)
        self.signal_expr_line = QLineEdit()
        self.signal_expr_line.setToolTip(
            "Expression to calculate the signal value, as a Numpy array."
        )
        _l.addWidget(self.signal_expr_line, 1, 1, 1, 1)
        _w.setLayout(_l)

        layout.addWidget(_w)

        help = QWidget()
        layout = QVBoxLayout()
        help.setLayout(layout)
        self.addWidget(help)

        text_area = QTextEdit(
            """
This interface can add arbitrary expressions to the plot, calculated using other signals as reference.
<br><br>
Any expression that generates a numpy array of the appropriate size can be added.
<br><br>
For instance, to generate a copy of a signal <code>abc</code> we can input the
expression <code>abc</code>, and for a version with all its values doubled in magnitude, an
expression like <code>2*abc</code> would work.
<br><br>
Other examples:
<br><br>
Using numpy: <code>np.gradient(abc, edge_order=2)</code>
<br>
Multiple inputs: <code>abc - np.log(xyz)</code>
<br><br><br>
Aside from the direct usage of <code>np</code>, for convenience, the following operations are also available:
<br><br>
<code>log | log10 | (a)sin | (a)cos | (a)tan</code>
""",
            readOnly=True,
        )
        text_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(text_area)

    def get_custom_signal_parameters(self):
        return self.signal_name_line.text(), self.signal_expr_line.text()

    def validate_expression(self, expression) -> tuple[bool, Exception | None]:
        import numpy as np

        environment = CUSTOM_SIGNALS_ENVIRONMENT
        for detector in self._expr_signal_names:
            environment[detector] = np.array([1, 2, 3])

        try:
            eval(expression, locals=environment)

            return True, None
        except Exception as e:
            return False, e

    def toggle_help(self):
        self.setCurrentIndex((self.currentIndex() + 1) % 2)
