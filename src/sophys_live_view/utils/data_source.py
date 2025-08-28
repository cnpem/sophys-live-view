from qtpy.QtCore import QThread, Signal


class DataSource(QThread):
    new_data_stream = Signal(str, str, set)  # uid, display_name, fields
    new_data_received = Signal(str, dict)  # uid, {signal : data}
