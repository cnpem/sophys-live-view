from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class RunSelector(QWidget):
    select_item = Signal(QListWidgetItem)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._parent = parent

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._run_list = QListWidget()
        self._run_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._run_list)

        self._parent.data_source_manager.new_data_stream.connect(self._add_stream)
        self._run_list.itemSelectionChanged.connect(self.change_current_streams)

        self.select_item.connect(
            self.on_select_item, Qt.ConnectionType.QueuedConnection
        )

    def change_current_streams(self):
        current_uids = []
        for item in self._run_list.selectedItems():
            current_uids.append((item.data(Qt.ItemDataRole.UserRole + 1), item.text()))
        self._parent.plot_display.change_current_streams(current_uids)
        self._parent.signal_selector.change_current_streams(current_uids)
        self._parent.metadata_viewer.change_current_streams(current_uids)

    def _add_stream(
        self,
        uid: str,
        subuid: str,
        display_name: str,
        signals: set[str],
        metadata: dict,
    ):
        item = QListWidgetItem()
        item.setText(display_name)
        item.setData(Qt.ItemDataRole.UserRole, uid)
        item.setData(Qt.ItemDataRole.UserRole + 1, subuid)
        self._run_list.addItem(item)

        self.select_item.emit(item)

    @Slot(QListWidgetItem)
    def on_select_item(self, item: QListWidgetItem):
        self._run_list.clearSelection()
        self._run_list.setCurrentItem(item)
