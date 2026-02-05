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
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .interfaces import CUSTOM_SIGNALS_ENVIRONMENT, ISignalSelector


def set_checked_no_emit(widget: QCheckBox | QRadioButton, state: bool):
    widget.blockSignals(True)
    widget.setChecked(state)
    widget.blockSignals(False)


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

        self._configure_default_signals(new_uids, new_signals)

        self._1d_signal_selection_table.configure_signals(new_uids, new_signals)
        self._2d_signal_selection_table.configure_signals(new_uids, new_signals)

    def _configure_default_signals(self, new_uids, new_signals):
        self.default_independent_signals = list()
        self.default_dependent_signals = set()

        for uid in new_uids:
            self.default_independent_signals.extend(
                self._default_independent_signals.get(uid, [])
            )
            self.default_dependent_signals |= self._default_dependent_signals.get(
                uid, set()
            )

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

        self._signal_selection_stack.currentWidget().refresh_layout()

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


class TableScrollArea(QScrollArea):
    def __init__(self, parent):
        super().__init__(parent)

        self._parent = parent

        self._row_widgets = list()

        self._layout = QGridLayout()
        self._layout.setRowMinimumHeight(0, 20)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def refresh_layout(self):
        # NOTE: We need to add a new widget so that the Scroll Area updates the layout.
        _w = QWidget()
        _w.setLayout(self._layout)

        # Take the old widget without destroying it, so it doesn't recursively destroy the layout (i guess)
        _old = self.takeWidget()

        self.setWidget(_w)
        area_size = self.viewport().size()
        _w.setMinimumSize(area_size)

    def _clear_layout(self):
        for widgets in self._row_widgets:
            for widget in widgets:
                self._layout.removeWidget(widget)

        self._row_widgets.clear()

    def _add_row(self, *args):
        row_count = len(self._row_widgets) + 1

        alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter

        for idx, widget in enumerate(args):
            self._layout.addWidget(widget, row_count, idx, 1, 1, alignment)

        self._layout.setRowMinimumHeight(row_count, 20)

        self._row_widgets.append(tuple(args))


class SelectionTable1D(TableScrollArea):
    selected_streams_changed = Signal(str, set)  # X, Y

    def __init__(self, parent):
        super().__init__(parent)

        self._selected_x_signal = ""
        self._selected_y_signals = set()

        self._old_independent_signals = list()
        self._old_dependent_signals = set()

        self._row_data = dict()

        alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter

        name = QLabel("Signal")
        name.setAlignment(alignment)
        self._layout.addWidget(name, 0, 0, 1, 1)
        x_axis = QLabel("X")
        x_axis.setAlignment(alignment)
        self._layout.addWidget(x_axis, 0, 1, 1, 1)
        y_axis = QLabel("Y")
        y_axis.setAlignment(alignment)
        self._layout.addWidget(y_axis, 0, 2, 1, 1)

        self._layout.setColumnStretch(0, 2)
        self._layout.setColumnStretch(1, 1)
        self._layout.setColumnStretch(2, 1)

        self.refresh_layout()

    def _row_signal_name(self, row: int):
        return self._row_widgets[row][0].text()

    def _row_signal(self, row: int):
        return self._row_data[self._row_signal_name(row)]

    def _is_x_axis_activated(self, row: int):
        return self._row_widgets[row][1].isChecked()

    def _activated_x_axis_rows(self):
        return [
            row
            for row in range(len(self._row_widgets))
            if self._is_x_axis_activated(row)
        ]

    def _is_y_axis_activated(self, row: int):
        return self._row_widgets[row][2].isChecked()

    def _activated_y_axis_rows(self):
        return [
            row
            for row in range(len(self._row_widgets))
            if self._is_y_axis_activated(row)
        ]

    def configure_signals(self, uids, signals):
        self._clear_layout()
        self._row_data.clear()

        sorted_signals_list = sorted(signals)
        for signal in sorted_signals_list:
            signal_name = self._parent.get_signal_name(signal)
            self._row_data[signal_name] = signal

            name = QLabel(signal_name)
            name.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
            )
            if "(custom)" in signal_name:
                _f = name.font()
                _f.setItalic(True)
                name.setFont(_f)

            x_axis_radio_button = QRadioButton()
            x_axis_radio_button.clicked.connect(self._change_x_axis_signal)

            y_axis_checkbox = QCheckBox()
            y_axis_checkbox.toggled.connect(self._change_y_axis_signals)

            self._add_row(name, x_axis_radio_button, y_axis_checkbox)

        self._select_default_x_axis_signal(signals)
        self._select_default_y_axis_signals(signals)

        # NOTE: Avoid sending essentially the same signal twice in a row.
        self._change_x_axis_signal(emit=False)
        self._change_y_axis_signals()

        self.refresh_layout()

    def _select_default_x_axis_signal(self, signals):
        """Select the default X axis signal if it's available, with more priority to old selected signals."""
        default_independent_signals = self._parent.default_independent_signals

        has_independent = any(s in self._old_independent_signals for s in signals)
        if has_independent:
            default_independent_signals = self._old_independent_signals

        for row in range(len(self._row_widgets)):
            signal = self._row_signal(row)
            if signal in default_independent_signals:
                set_checked_no_emit(self._row_widgets[row][1], True)
                return

    def _get_selected_x_axis_signal(self):
        for row in self._activated_x_axis_rows():
            return self._row_signal(row)

    def _select_default_y_axis_signals(self, signals):
        """Select the default Y axis signals if they're available, with more priority to old selected signals."""
        default_dependent_signals = self._parent.default_dependent_signals

        has_dependent = any(s in self._old_dependent_signals for s in signals)
        if has_dependent:
            default_dependent_signals = self._old_dependent_signals

        for row in range(len(self._row_widgets)):
            signal = self._row_signal(row)
            if signal in default_dependent_signals:
                set_checked_no_emit(self._row_widgets[row][2], True)

    def _get_selected_y_axis_signals(self):
        selected_signals = set()

        for row in self._activated_y_axis_rows():
            selected_signals.add(self._row_signal(row))

        return selected_signals

    def _change_x_axis_signal(self, emit=True):
        self._selected_x_signal = self._get_selected_x_axis_signal()
        self._old_independent_signals = [self._selected_x_signal]

        if emit:
            self.selected_streams_changed.emit(
                self._selected_x_signal, self._selected_y_signals
            )

    def _change_y_axis_signals(self, emit=True):
        self._selected_y_signals = self._get_selected_y_axis_signals()
        self._old_dependent_signals = set(self._selected_y_signals)

        if emit:
            self.selected_streams_changed.emit(
                self._selected_x_signal, self._selected_y_signals
            )


class SelectionTable2D(TableScrollArea):
    selected_streams_changed = Signal(str, str, set)  # X, Y, Z

    def __init__(self, parent):
        super().__init__(parent)

        self._selected_x_signal = ""
        self._selected_y_signal = ""
        self._selected_z_signal = ""

        self._old_independent_signals = list()
        self._old_dependent_signals = set()

        self._x_buttons_container = QButtonGroup()
        self._y_buttons_container = QButtonGroup()
        self._z_buttons_container = QButtonGroup()

        self._row_data = dict()

        alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter

        name = QLabel("Signal")
        name.setAlignment(alignment)
        self._layout.addWidget(name, 0, 0, 1, 1)
        x_axis = QLabel("X")
        x_axis.setAlignment(alignment)
        self._layout.addWidget(x_axis, 0, 1, 1, 1)
        y_axis = QLabel("Y")
        y_axis.setAlignment(alignment)
        self._layout.addWidget(y_axis, 0, 2, 1, 1)
        data_axis = QLabel("Data")
        data_axis.setAlignment(alignment)
        self._layout.addWidget(data_axis, 0, 3, 1, 1)

        self._layout.setColumnStretch(0, 2)
        self._layout.setColumnStretch(1, 1)
        self._layout.setColumnStretch(2, 1)
        self._layout.setColumnStretch(3, 1)

        self.refresh_layout()

    def configure_signals(self, uids, signals):
        self._clear_layout()
        self._row_data.clear()

        sorted_signals_list = sorted(signals)
        for signal in sorted_signals_list:
            signal_name = self._parent.get_signal_name(signal)
            self._row_data[signal_name] = signal

            name = QLabel(signal_name)
            name.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter
            )
            if "(custom)" in signal_name:
                _f = name.font()
                _f.setItalic(True)
                name.setFont(_f)

            x_axis_radio_button = QRadioButton()
            x_axis_radio_button.clicked.connect(self._change_x_axis_signal)
            self._x_buttons_container.addButton(x_axis_radio_button)

            y_axis_radio_button = QRadioButton()
            y_axis_radio_button.clicked.connect(self._change_y_axis_signal)
            self._y_buttons_container.addButton(y_axis_radio_button)

            z_axis_radio_button = QRadioButton()
            z_axis_radio_button.clicked.connect(self._change_z_axis_signal)
            self._z_buttons_container.addButton(z_axis_radio_button)

            self._add_row(
                name, x_axis_radio_button, y_axis_radio_button, z_axis_radio_button
            )

        self._select_default_x_axis_signal(signals)
        self._select_default_y_axis_signal(signals)
        self._select_default_z_axis_signal(signals)

        self._change_x_axis_signal(emit=False)
        self._change_y_axis_signal(emit=False)
        self._change_z_axis_signal()

        self.refresh_layout()

    def _row_signal_name(self, row: int):
        return self._row_widgets[row][0].text()

    def _row_signal(self, row: int):
        return self._row_data[self._row_signal_name(row)]

    def _is_x_axis_activated(self, row: int):
        return self._row_widgets[row][1].isChecked()

    def _activated_x_axis_rows(self):
        return [
            row
            for row in range(len(self._row_widgets))
            if self._is_x_axis_activated(row)
        ]

    def _is_y_axis_activated(self, row: int):
        return self._row_widgets[row][2].isChecked()

    def _activated_y_axis_rows(self):
        return [
            row
            for row in range(len(self._row_widgets))
            if self._is_y_axis_activated(row)
        ]

    def _is_z_axis_activated(self, row: int):
        return self._row_widgets[row][3].isChecked()

    def _activated_z_axis_rows(self):
        return [
            row
            for row in range(len(self._row_widgets))
            if self._is_z_axis_activated(row)
        ]

    def _select_default_x_axis_signal(self, signals):
        """Select the default X axis signal if it's available, with more priority to old selected signals."""
        default_independent_signals = self._parent.default_independent_signals

        has_independent = any(s in self._old_independent_signals for s in signals)
        if has_independent:
            default_independent_signals = self._old_independent_signals

        if len(default_independent_signals) < 2:
            return

        for row in range(len(self._row_widgets)):
            signal = self._row_signal(row)
            if signal == default_independent_signals[1]:
                set_checked_no_emit(self._row_widgets[row][1], True)
                return

    def _get_selected_x_axis_signal(self):
        for row in self._activated_x_axis_rows():
            return self._row_signal(row)

    def _select_default_y_axis_signal(self, signals):
        """Select the default Y axis signal if it's available, with more priority to old selected signals."""
        default_independent_signals = self._parent.default_independent_signals

        has_independent = any(s in self._old_independent_signals for s in signals)
        if has_independent:
            default_independent_signals = self._old_independent_signals

        if len(default_independent_signals) < 2:
            return

        for row in range(len(self._row_widgets)):
            signal = self._row_signal(row)
            if signal == default_independent_signals[0]:
                set_checked_no_emit(self._row_widgets[row][2], True)
                return

    def _get_selected_y_axis_signal(self):
        for row in self._activated_y_axis_rows():
            return self._row_signal(row)

    def _select_default_z_axis_signal(self, signals):
        """Select the default Z axis signal if it's available, with more priority to old selected signals."""
        default_dependent_signals = self._parent.default_dependent_signals

        has_dependent = any(s in self._old_dependent_signals for s in signals)
        if has_dependent:
            default_dependent_signals = self._old_dependent_signals

        for row in range(len(self._row_widgets)):
            signal = self._row_signal(row)
            if signal in default_dependent_signals:
                set_checked_no_emit(self._row_widgets[row][3], True)
                return

    def _get_selected_z_axis_signal(self):
        for row in self._activated_z_axis_rows():
            return self._row_signal(row)

    def _change_x_axis_signal(self, emit=True):
        self._selected_x_signal = self._get_selected_x_axis_signal()
        self._parent._old_independent_signals = [
            self._selected_x_signal,
            self._selected_y_signal,
        ]

        if emit:
            self.selected_streams_changed.emit(
                self._selected_x_signal,
                self._selected_y_signal,
                self._selected_z_signal,
            )

    def _change_y_axis_signal(self, emit=True):
        self._selected_y_signal = self._get_selected_y_axis_signal()
        self._parent._old_independent_signals = [
            self._selected_x_signal,
            self._selected_y_signal,
        ]

        if emit:
            self.selected_streams_changed.emit(
                self._selected_x_signal,
                self._selected_y_signal,
                self._selected_z_signal,
            )

    def _change_z_axis_signal(self, emit=True):
        self._selected_z_signal = self._get_selected_z_axis_signal()
        self._parent._old_dependent_signals = set([self._selected_z_signal])

        if emit:
            self.selected_streams_changed.emit(
                self._selected_x_signal,
                self._selected_y_signal,
                self._selected_z_signal,
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
