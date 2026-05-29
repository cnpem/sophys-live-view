from dataclasses import dataclass
from enum import IntEnum, auto
from time import localtime, strftime
from typing import Any, TypeAlias

import qtawesome as qta
from qtpy.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QPersistentModelIndex,
    QRect,
    QSize,
    Qt,
    Signal,
    Slot,
)
from qtpy.QtGui import QFont, QPainter, QTextOption
from qtpy.QtWidgets import (
    QFileDialog,
    QLabel,
    QListView,
    QProgressBar,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
)

from ..utils.json_data_source import JSONDataSource
from .interfaces import IRunSelector


class RunSelector(IRunSelector):
    select_item = Signal(QModelIndex)

    def __init__(self, data_source_manager):
        super().__init__()

        self._data_source_manager = data_source_manager

        self._go_to_last_automatically = True
        self._finished_loading = False

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._run_list_model = RunListModel()
        self._run_list_view = QListView()
        self._run_list_view.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        self._run_list_view.setModel(self._run_list_model)
        self._run_list_view.setItemDelegateForColumn(0, RunItem.create_item_delegate())
        layout.addWidget(self._run_list_view)

        self._progress_label = QLabel()
        self._progress_label.setVisible(False)
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._progress_label)

        self._progress_progress_bar = QProgressBar()
        self._progress_progress_bar.setVisible(False)
        self._progress_progress_bar.setRange(0, 100)
        layout.addWidget(self._progress_progress_bar)

        self._file_import_button = QPushButton("Import from file...")
        self._file_import_button.clicked.connect(self._import_file)
        layout.addWidget(self._file_import_button)

        data_source_manager.new_data_stream.connect(self._add_stream)
        data_source_manager.data_stream_closed.connect(self._close_stream)
        data_source_manager.go_to_last_automatically.connect(self._set_go_to_last)
        data_source_manager.loading_status.connect(self._new_loading_status)
        self._run_list_view.selectionModel().selectionChanged.connect(
            self.change_current_streams
        )
        self._run_list_view.doubleClicked.connect(self.toggle_bookmark)

        self.select_item.connect(
            self.on_select_item, Qt.ConnectionType.QueuedConnection
        )

    def change_current_streams(self):
        current_streams = []
        for index in self._run_list_view.selectedIndexes():
            text = self._run_list_model.data(index, Qt.ItemDataRole.DisplayRole)
            subuid = self._run_list_model.data(index, RunListModelRoles.SUBUID_ROLE)

            current_streams.append((subuid, text))

        self.selected_streams_changed.emit(current_streams)

    def _add_stream(
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
        self._run_list_model.add_stream(uid, subuid, display_name, metadata)

        if self._finished_loading and self._go_to_last_automatically:
            self.select_item.emit(
                self._run_list_model.index(self._run_list_model.rowCount() - 1, 0)
            )

    def _close_stream(self, uid: str, subuid: str, timestamp: int):
        self._run_list_model.close_stream(uid, subuid, timestamp)

    @Slot(QModelIndex)
    def on_select_item(self, index: QModelIndex):
        self._run_list_view.selectionModel().clearSelection()
        self._run_list_view.setCurrentIndex(index)

    @Slot(QModelIndex)
    def toggle_bookmark(self, index: QModelIndex):
        currently_checked = self._run_list_model.data(
            index, RunListModelRoles.BOOKMARK_ROLE
        )
        self._run_list_model.setData(
            index, not currently_checked, RunListModelRoles.BOOKMARK_ROLE
        )

    @Slot(str, bool)
    def _set_go_to_last(self, uid: str, state: bool):
        self._go_to_last_automatically = state

    @Slot(str, str, float)
    def _new_loading_status(self, uid: str, message: str, percentage: float):
        if percentage >= 100.0:
            self._progress_label.setVisible(False)
            self._progress_progress_bar.setVisible(False)

            self._finished_loading = True
            item_count = self._run_list_model.rowCount()
            if self._go_to_last_automatically and item_count > 0:
                self.select_item.emit(self._run_list_model.index(item_count - 1, 0))
        else:
            self._progress_label.setVisible(True)
            self._progress_label.setText(message)
            self._progress_progress_bar.setVisible(True)
            self._progress_progress_bar.setValue(round(percentage))

            self._finished_loading = False

    def _import_file(self):
        file_names, selected_filter = QFileDialog.getOpenFileNames(
            caption="Select a file to load into sophys-live-view.",
            filter="JSON (*.json)",
        )
        if len(file_names) == 0:
            return

        for file_name in file_names:
            data_source = JSONDataSource(file_name)
            self._data_source_manager.add_data_source(data_source)


ModelIndex: TypeAlias = QModelIndex | QPersistentModelIndex
MaybeModelIndex: TypeAlias = ModelIndex | None


@dataclass
class RunItem:
    uid: str
    subuid: str
    display_name: str

    bookmarked: bool = False
    loading: bool = False

    start_time: float | None = None
    end_time: float | None = None

    class RunItemDelegate(QStyledItemDelegate):
        def sizeHint(self, option: QStyleOptionViewItem, index: ModelIndex) -> QSize:  # noqa: N802
            return QSize(option.rect.width(), option.fontMetrics.height() * 2)

        def paint(
            self, painter: QPainter, option: QStyleOptionViewItem, index: ModelIndex
        ):
            self.initStyleOption(option, index)

            first_line_rect = QRect(option.rect)
            first_line_rect.setHeight(option.fontMetrics.height())
            second_line_rect = QRect(option.rect)
            second_line_rect.setHeight(option.fontMetrics.height())
            second_line_rect.translate(0, first_line_rect.height())

            option.decorationAlignment = (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            option.decorationSize = QSize(
                option.decorationSize.width(), first_line_rect.height()
            )
            option.displayAlignment = (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            super().paint(painter, option, index)

            second_line_text_opts = QTextOption(Qt.AlignmentFlag.AlignVCenter)
            second_line_text_opts.setWrapMode(QTextOption.WrapMode.NoWrap)

            start_time = strftime(
                "%d/%m/%Y %H:%M:%S ",
                localtime(int(index.data(role=RunListModelRoles.START_TIME_ROLE))),
            )
            start_time_font = QFont(option.font)
            start_time_font.setPixelSize(10)

            try:
                end_time = strftime(
                    "%d/%m/%Y %H:%M:%S ",
                    localtime(int(index.data(role=RunListModelRoles.END_TIME_ROLE))),
                )
            except TypeError:
                end_time = "-"
            end_time_font = QFont(option.font)
            end_time_font.setPixelSize(10)

            painter.save()
            painter.setFont(start_time_font)
            painter.setClipRect(second_line_rect)
            painter.drawText(
                second_line_rect,
                f" Start time: {start_time} | End time: {end_time}",
                second_line_text_opts,
            )
            painter.restore()

    @classmethod
    def create_item_delegate(cls) -> QStyledItemDelegate:
        return cls.RunItemDelegate()


class RunListModelRoles(IntEnum):
    UID_ROLE = Qt.ItemDataRole.UserRole
    SUBUID_ROLE = auto()

    BOOKMARK_ROLE = auto()
    LOADING_ROLE = auto()

    START_TIME_ROLE = auto()
    END_TIME_ROLE = auto()


class RunListModel(QAbstractItemModel):
    def __init__(self):
        super().__init__()

        self._runs = list()

        self.star_unfilled_icon = qta.icon("fa6.star", scale_factor=0.8)
        self.star_filled_icon = qta.icon("fa6s.star", color="orange", scale_factor=0.8)
        self.loading_icon = qta.icon("fa6s.spinner", scale_factor=0.8)

    def add_stream(
        self,
        uid: str,
        subuid: str,
        display_name: str,
        metadata: dict[str, Any],
    ):
        old_number_of_items = len(self._runs)
        self.rowsAboutToBeInserted.emit(
            QModelIndex(), old_number_of_items, old_number_of_items
        )
        self._runs.append(
            RunItem(
                uid, subuid, display_name, loading=True, start_time=metadata.get("time")
            )
        )
        self.rowsInserted.emit(QModelIndex(), old_number_of_items, old_number_of_items)

    def close_stream(self, uid: str, subuid: str, timestamp: int):
        for rev_index, run in enumerate(reversed(self._runs)):
            if run.uid == uid and run.subuid == subuid:
                run.loading = False

                row = self.rowCount() - rev_index - 1
                index = self.index(row, 0)

                self.setData(index, timestamp, role=RunListModelRoles.END_TIME_ROLE)
                self.dataChanged.emit(index, index)

                break

    def rowCount(self, parent: MaybeModelIndex = None):  # noqa: N802
        return len(self._runs)

    def columnCount(self, parent: MaybeModelIndex = None):  # noqa: N802
        return 1

    def index(self, row: int, column: int, parent: MaybeModelIndex = None):
        return self.createIndex(row, column)

    def parent(self, index: ModelIndex):  # ty: ignore
        if index.column() == 0:
            return QModelIndex()

        return self.createIndex(index.row(), 0)

    def data(self, index: ModelIndex, role=Qt.ItemDataRole.DisplayRole):
        item = self._runs[index.row()]
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return item.display_name
            case Qt.ItemDataRole.DecorationRole:
                icon = (
                    self.star_filled_icon
                    if item.bookmarked
                    else self.star_unfilled_icon
                )

                if item.loading:
                    icon = self.loading_icon

                return icon
            case Qt.ItemDataRole.SizeHintRole:
                return QSize(22, 22)
            case Qt.ItemDataRole.ToolTipRole:
                return "Double-click to mark this item in the list."
            case RunListModelRoles.UID_ROLE:
                return item.uid
            case RunListModelRoles.SUBUID_ROLE:
                return item.subuid
            case RunListModelRoles.BOOKMARK_ROLE:
                return item.bookmarked
            case RunListModelRoles.LOADING_ROLE:
                return item.loading
            case RunListModelRoles.START_TIME_ROLE:
                return item.start_time
            case RunListModelRoles.END_TIME_ROLE:
                return item.end_time
            case _:
                return None

    def setData(self, index: ModelIndex, data, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        item = self._runs[index.row()]
        match role:
            case RunListModelRoles.BOOKMARK_ROLE:
                item.bookmarked = bool(data)
            case RunListModelRoles.LOADING_ROLE:
                item.loading = bool(data)
            case RunListModelRoles.END_TIME_ROLE:
                item.end_time = int(data)
            case _:
                return True

        self.dataChanged.emit(index, index, [role])
        return True
