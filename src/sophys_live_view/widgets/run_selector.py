from dataclasses import dataclass

import qtawesome as qta
from qtpy.QtCore import QAbstractListModel, QModelIndex, QSize, Qt, Signal, Slot
from qtpy.QtWidgets import (
    QFileDialog,
    QLabel,
    QListView,
    QProgressBar,
    QPushButton,
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
            subuid = self._run_list_model.data(index, RunListModel.SUBUID_ROLE)

            current_streams.append((subuid, text))

        self.selected_streams_changed.emit(current_streams)

    def _add_stream(
        self,
        uid: str,
        subuid: str,
        display_name: str,
        signals: set[str],
        metadata: dict,
    ):
        self._run_list_model.add_stream(uid, subuid, display_name)

        if self._finished_loading and self._go_to_last_automatically:
            self.select_item.emit(
                self._run_list_model.index(self._run_list_model.rowCount() - 1)
            )

    def _close_stream(
        self,
        uid: str,
        subuid: str,
    ):
        self._run_list_model.close_stream(uid, subuid)

    @Slot(QModelIndex)
    def on_select_item(self, index: QModelIndex):
        self._run_list_view.selectionModel().clearSelection()
        self._run_list_view.setCurrentIndex(index)

    @Slot(QModelIndex)
    def toggle_bookmark(self, index: QModelIndex):
        currently_checked = self._run_list_model.data(index, RunListModel.BOOKMARK_ROLE)
        self._run_list_model.setData(
            index, not currently_checked, RunListModel.BOOKMARK_ROLE
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
                self.select_item.emit(self._run_list_model.index(item_count - 1))
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


@dataclass
class RunItem:
    uid: str
    subuid: str
    display_name: str

    bookmarked: bool = False
    loading: bool = False


class RunListModel(QAbstractListModel):
    UID_ROLE = Qt.ItemDataRole.UserRole
    SUBUID_ROLE = Qt.ItemDataRole.UserRole + 1
    BOOKMARK_ROLE = Qt.ItemDataRole.UserRole + 2
    LOADING_ROLE = Qt.ItemDataRole.UserRole + 3

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
    ):
        old_number_of_items = len(self._runs)
        self.rowsAboutToBeInserted.emit(
            QModelIndex(), old_number_of_items, old_number_of_items
        )
        self._runs.append(RunItem(uid, subuid, display_name, loading=True))
        self.rowsInserted.emit(QModelIndex(), old_number_of_items, old_number_of_items)

    def close_stream(self, uid: str, subuid: str):
        for rev_index, run in enumerate(reversed(self._runs)):
            if run.uid == uid and run.subuid == subuid:
                run.loading = False

                index = self.index(self.rowCount() - rev_index)
                self.dataChanged.emit(index, index)

                break

    def rowCount(self, parent: QModelIndex | None = None):  # noqa: N802
        return len(self._runs)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
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
            case RunListModel.UID_ROLE:
                return item.uid
            case RunListModel.SUBUID_ROLE:
                return item.subuid
            case RunListModel.BOOKMARK_ROLE:
                return item.bookmarked
            case RunListModel.LOADING_ROLE:
                return item.loading
            case _:
                return None

    def setData(self, index: QModelIndex, data, role):  # noqa: N802
        item = self._runs[index.row()]
        match role:
            case RunListModel.BOOKMARK_ROLE:
                item.bookmarked = bool(data)
            case RunListModel.LOADING_ROLE:
                item.loading = bool(data)
            case _:
                return True

        self.dataChanged.emit(index, index, [role])
        return True
