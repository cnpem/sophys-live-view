from abc import abstractmethod

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget


class IRunSelector(QWidget):
    """
    Manager for streams, bookmarks (favorites), and creator of new DataSources.

    This class is responsible for handling selection of streams, and propagating
    that to other parts of the application via its signal. It also handles bookmarks
    internally and creates new DataSources based on the import criterion.

    This object provides the `selected_streams_changed` signal, which is used by
    other components to react to a change in run selection (e.g. update the data
    plotted, or the metadata visualization).

    Parameters
    ----------
    data_source_manager : DataSourceManager
        The object that will be responsible for handling us the metadata.
    """

    selected_streams_changed = Signal(list)  # List of (uid, stream name)


class IMetadataViewer(QWidget):
    """
    Metadata visualization for one or more streams.

    This entity is responsible for displaying a table with metadata keys
    and values pertaining to one or more selected streams.

    Parameters
    ----------
    data_source_manager : DataSourceManager
        The object that will be responsible for handling us the metadata.
    selected_streams_changed : Signal
        The signal that will be emitted when a new set of streams is selected.
    """


class ISignalSelector(QWidget):
    """
    Select independent and dependent axis of data for display.

    This class is responsible for handling the selection and deselection
    of signals to be used by `PlotDisplay` for plotting data.
    It communicates with that entity through its two signals, that get
    emitted when the configuration changes, or when the selected stream changes.

    This object also reacts to new stream selections, updating the available
    signals accordingly (including telling `PlotDisplay` which signals to plot
    as the default right after switching streams), and reacts to changes in
    the plotted type of data, adapting itself to handle 1D or 2D data.

    Parameters
    ----------
    data_source_manager : DataSourceManager
        The object that will be responsible for handling us the data.
    selected_streams_changed : Signal
        The signal that will be emitted when a new set of streams is selected.
    """

    selected_signals_changed_1d = Signal(str, set)  # X, Y
    selected_signals_changed_2d = Signal(str, str, set)  # X, Y, Z

    @abstractmethod
    def set_plot_tab_changed_signal(self, signal: Signal):
        """
        Configure a signal that tells the widget that the data visualization has
        changed, so maybe it should update itself. The signal is expected to have
        a string parameter, telling which type of visualization is now selected.
        """
        raise NotImplementedError


class IPlotDisplay(QWidget):
    """
    Maintain and organize plotting capabilities.

    This class is responsible for handling incoming data from the application,
    and translating that into visual plots, using its configured properties.
    It uses an internal object, instance of `DataAccumulator`, to join and store
    the data it receives, and uses that to plot data points on-demand.

    Parameters
    ----------
    data_source_manager : DataSourceManager
        The object that will be responsible for handling us the data.
    selected_streams_changed : Signal
        The signal that will be emitted when a new set of streams is selected.
    selected_signals_changed_1d : Signal
        The signal that will be emitted with a new 1D signals configuration.
    selected_signals_changed_2d : Signal
        The signal that will be emitted with a new 2D signals configuration.
    show_stats_by_default : bool, optional
        Whether to show a widget with curve statistics by default on the 1D plot.
    """

    plot_tab_changed = Signal(str)  # new tab name
