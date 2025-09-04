from qtpy.QtCore import QThread, Signal


class DataSource(QThread):
    new_data_stream = Signal(
        str, str, set, set, list, dict
    )  # uid, display_name, fields, detectors, motors, metadata
    new_data_received = Signal(
        str, dict, dict
    )  # uid, {signal : data}, {signal : metadata}
    go_to_last_automatically = Signal(bool)  # Whether to auto-update the display or not
    loading_status = Signal(str, float)  # status message, completion percentage

    def start_thread(self):
        """Start processing this DataSource."""
        QThread.start(self)

    def close_thread(self):
        """Stop processing this DataSource."""
        QThread.terminate(self)
