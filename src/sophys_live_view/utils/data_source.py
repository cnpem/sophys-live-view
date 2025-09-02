from qtpy.QtCore import QThread, Signal


class DataSource(QThread):
    new_data_stream = Signal(
        str, str, set, set, list, dict
    )  # uid, display_name, fields, detectors, motors, metadata
    new_data_received = Signal(
        str, dict, dict
    )  # uid, {signal : data}, {signal : metadata}
