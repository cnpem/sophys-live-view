import qtawesome as qta
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class RunSelector(QWidget):
    select_item = Signal(QListWidgetItem)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._parent = parent

        self._go_to_last_automatically = True

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._run_list = QListWidget()
        self._run_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._run_list)

        self._parent.data_source_manager.new_data_stream.connect(self._add_stream)
        self._parent.data_source_manager.go_to_last_automatically.connect(
            self._set_go_to_last
        )
        self._run_list.itemSelectionChanged.connect(self.change_current_streams)
        self._run_list.itemDoubleClicked.connect(self.toggle_bookmark)

        self.select_item.connect(
            self.on_select_item, Qt.ConnectionType.QueuedConnection
        )

        self.star_unfilled_icon = qta.icon("fa6.star", scale_factor=0.8)
        self.star_filled_icon = qta.icon("fa6s.star", color="orange", scale_factor=0.8)

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
        item.setData(Qt.ItemDataRole.UserRole + 2, False)
        item.setData(Qt.ItemDataRole.DecorationRole, self.star_unfilled_icon)
        item.setData(Qt.ItemDataRole.SizeHintRole, QSize(22, 22))
        item.setToolTip("Double-click to mark this item in the list.")
        self._run_list.addItem(item)

        if self._go_to_last_automatically:
            self.select_item.emit(item)

    @Slot(QListWidgetItem)
    def on_select_item(self, item: QListWidgetItem):
        self._run_list.clearSelection()
        self._run_list.setCurrentItem(item)

    @Slot(QListWidgetItem)
    def toggle_bookmark(self, item: QListWidgetItem):
        currently_checked = item.data(Qt.ItemDataRole.UserRole + 2)
        if currently_checked:
            item.setData(Qt.ItemDataRole.DecorationRole, self.star_unfilled_icon)
            item.setData(Qt.ItemDataRole.UserRole + 2, False)
        else:
            item.setData(Qt.ItemDataRole.DecorationRole, self.star_filled_icon)
            item.setData(Qt.ItemDataRole.UserRole + 2, True)

    @Slot(str, bool)
    def _set_go_to_last(self, uid: str, state: bool):
        self._go_to_last_automatically = state
