from importlib.metadata import version

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QMainWindow, QSplitter

from ..utils.data_source_manager import DataSourceManager
from .metadata_viewer import MetadataViewer
from .plot_display import PlotDisplay
from .run_selector import RunSelector
from .signal_selector import SignalSelector


class SophysLiveView(QMainWindow):
    def __init__(self, data_sources, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.resize(1200, 800)
        self.setWindowTitle(
            "sophys-live-view - version {}".format(version("sophys-live-view"))
        )

        self.data_source_manager = DataSourceManager()

        self.run_selector = RunSelector(self.data_source_manager)
        self.metadata_viewer = MetadataViewer(
            self.data_source_manager, self.run_selector.selected_streams_changed
        )
        self.signal_selector = SignalSelector(
            self.data_source_manager, self.run_selector.selected_streams_changed
        )
        self.plot_display = PlotDisplay(
            self.data_source_manager,
            self.run_selector.selected_streams_changed,
            self.signal_selector.selected_signals_changed_1d,
            self.signal_selector.selected_signals_changed_2d,
        )

        self.signal_selector.set_plot_tab_changed_signal(
            self.plot_display.plot_tab_changed
        )

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
        controls_display_splitter.addWidget(self.signal_selector)
        controls_display_splitter.setSizes([1, 3])

        self.setCentralWidget(vertical_splitter)

        for data_source in data_sources:
            self.data_source_manager.add_data_source(data_source)

        self.data_source_manager.start()

        QApplication.instance().lastWindowClosed.connect(self.data_source_manager.stop)
