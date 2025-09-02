from qtpy.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QTabWidget


class MetadataViewer(QTabWidget):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._parent = parent

        self._stream_metadata = dict()

        self._parent.data_source_manager.new_data_stream.connect(self._add_new_stream)

    def change_current_streams(self, new_uids_and_names: list[tuple[str, str]]):
        self.clear()

        for uid, name in new_uids_and_names:
            metadata_page = QTableWidget(columnCount=2)
            metadata_page.verticalHeader().setVisible(False)
            metadata_page.setHorizontalHeaderLabels(["Key", "Value"])
            metadata_page.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            metadata_page.horizontalHeader().setStretchLastSection(True)

            for metadata_key, metadata_value in self._stream_metadata[uid].items():
                key_item = QTableWidgetItem(str(metadata_key))
                value_item = QTableWidgetItem(str(metadata_value))

                index = metadata_page.rowCount()
                metadata_page.insertRow(index)
                metadata_page.setItem(index, 0, key_item)
                metadata_page.setItem(index, 1, value_item)

            self.addTab(metadata_page, name)

    def _add_new_stream(
        self,
        uid: str,
        subuid: str,
        display_name: str,
        signals: set[str],
        detectors: set[str],
        motors: set[str],
        metadata: dict,
    ):
        self._stream_metadata[subuid] = metadata
