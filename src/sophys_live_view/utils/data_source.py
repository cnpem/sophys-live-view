from qtpy.QtCore import QThread, Signal


class DataSource(QThread):
    new_data_stream = Signal(str, str, set, dict)  # uid, display_name, fields, metadata
    new_data_received = Signal(str, dict)  # uid, {signal : data}
