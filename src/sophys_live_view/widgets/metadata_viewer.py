from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHeaderView,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from silx.gui.widgets.TableWidget import TableWidget


class MetadataViewer(QWidget):
    def __init__(self, data_source_manager, change_streams_signal):
        """
        Metadata visualization for one or more streams.

        This entity is responsible for displaying a table with metadata keys
        and values pertaining to one or more selected streams.

        Parameters
        ----------
        data_source_manager : DataSourceManager
            The object that will be responsible for handling us the metadata.
        change_streams_signal : Signal
            The signal that will be emitted when a new set of streams is selected.
        """
        super().__init__()

        self._stream_metadata = dict()

        layout = QVBoxLayout()
        self._tab = QTabWidget()
        layout.addWidget(self._tab)
        self.setLayout(layout)

        data_source_manager.new_data_stream.connect(self._add_new_stream)
        change_streams_signal.connect(self.change_current_streams)

    def change_current_streams(self, new_uids_and_names: list[tuple[str, str]]):
        self._tab.clear()

        def add_metadata_field(key, value, metadata_page):
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    key_last_portion = key.split("-")[-1][1:]
                    if sub_key.startswith(key_last_portion):
                        sub_key = sub_key[len(key_last_portion) + 1 :]
                    add_metadata_field(key + " - " + sub_key, sub_val, metadata_page)
                return

            key_item = QTableWidgetItem(str(key))
            key_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignHCenter
            )
            value_item = QTableWidgetItem(str(value))

            index = metadata_page.rowCount()
            metadata_page.insertRow(index)
            metadata_page.setItem(index, 0, key_item)
            metadata_page.setItem(index, 1, value_item)

        for uid, name in new_uids_and_names:
            metadata_page = TableWidget()
            metadata_page.setColumnCount(2)
            metadata_page.verticalHeader().setVisible(False)
            metadata_page.setHorizontalHeaderLabels(["Key", "Value"])
            metadata_page.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            metadata_page.horizontalHeader().setStretchLastSection(True)

            for metadata_key, metadata_value in self._stream_metadata[uid].items():
                if (
                    metadata_key == "configuration"
                ):  # NOTE: Force 'configuration' to be at the end.
                    continue
                add_metadata_field(metadata_key, metadata_value, metadata_page)

            if "configuration" in self._stream_metadata[uid]:
                add_metadata_field(
                    "configuration",
                    self._stream_metadata[uid]["configuration"],
                    metadata_page,
                )

            self._tab.addTab(metadata_page, name)

    def _add_new_stream(
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
        self._stream_metadata[subuid] = metadata
