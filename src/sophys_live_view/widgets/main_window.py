from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QMainWindow, QSplitter, QTabWidget

from ..utils.data_source_manager import DataSourceManager
from ..utils.kafka_data_source import KafkaDataSource
from .metadata_viewer import MetadataViewer
from .plot_configuration import PlotConfiguration
from .plot_display import PlotDisplay
from .run_selector import RunSelector
from .signal_selector import SignalSelector


class SophysLiveView(QMainWindow):
    def __init__(self, kafka_topic, kafka_bootstrap_servers, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.resize(1200, 800)

        self.data_source_manager = DataSourceManager()

        self.metadata_viewer = MetadataViewer(self)
        self.plot_configuration = PlotConfiguration(self)
        self.plot_display = PlotDisplay(self)
        self.run_selector = RunSelector(self)
        self.signal_selector = SignalSelector(self)

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.setHandleWidth(10)

        main_display_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_display_splitter.setHandleWidth(10)
        controls_display_splitter = QSplitter(Qt.Orientation.Horizontal)
        controls_display_splitter.setHandleWidth(10)

        vertical_splitter.addWidget(main_display_splitter)
        vertical_splitter.addWidget(controls_display_splitter)
        vertical_splitter.setSizes([2, 1])

        main_display_splitter.addWidget(self.run_selector)
        main_display_splitter.addWidget(self.plot_display)
        main_display_splitter.setSizes([1, 4])

        controls_display_splitter.addWidget(self.metadata_viewer)
        plot_settings_widget = QTabWidget()
        plot_settings_widget.addTab(self.signal_selector, "Signals")
        plot_settings_widget.addTab(self.plot_configuration, "Configuration")
        controls_display_splitter.addWidget(plot_settings_widget)
        controls_display_splitter.setSizes([1, 3])

        self.setCentralWidget(vertical_splitter)

        kafka_data_source = KafkaDataSource(kafka_topic, kafka_bootstrap_servers)
        self.data_source_manager.add_data_source(kafka_data_source)

        self.data_source_manager.start()

        QApplication.instance().lastWindowClosed.connect(self.data_source_manager.stop)
