import pytest
from silx.gui.plot import Plot1D
from silx.gui.plot.actions import PlotAction

from sophys_live_view.widgets.plot_actions import DerivativeAction


@pytest.fixture
def base_1d_plot(qtbot):
    plot = Plot1D()
    qtbot.addWidget(plot)
    return plot


@pytest.fixture
def derivative_action(base_1d_plot, qtbot):
    return DerivativeAction(base_1d_plot, base_1d_plot)


def test_derivative_static(derivative_action: PlotAction, base_1d_plot: Plot1D, qtbot):
    base_1d_plot.addCurve([1, 2, 3, 4, 5], [1, 4, 9, 16, 25], legend="square")

    derivative_action.trigger()
    qtbot.waitUntil(lambda: len(base_1d_plot.getAllCurves()) == 2, timeout=1000)

    new_curve = base_1d_plot.getCurve("Derivative of square")
    assert new_curve is not None

    assert all(new_curve.getXData()[i] == [1, 2, 3, 4, 5][i] for i in range(5)), (
        new_curve.getXData()
    )
    assert all(new_curve.getYData()[i] == [2, 4, 6, 8, 10][i] for i in range(5)), (
        new_curve.getYData()
    )

    derivative_action.trigger()
    qtbot.waitUntil(lambda: len(base_1d_plot.getAllCurves()) == 1, timeout=1000)


def test_derivative_dynamic(derivative_action: PlotAction, base_1d_plot: Plot1D, qtbot):
    base_1d_plot.addCurve([1, 2, 3, 4, 5], [1, 4, 9, 16, 25], legend="square")

    derivative_action.trigger()
    qtbot.waitUntil(lambda: len(base_1d_plot.getAllCurves()) == 2, timeout=1000)

    base_1d_plot.remove("square")
    qtbot.waitUntil(lambda: len(base_1d_plot.getAllCurves()) == 0, timeout=1000)

    base_1d_plot.addCurve([6, 7, 8], [36, 49, 64], legend="square")
    qtbot.waitUntil(lambda: len(base_1d_plot.getAllCurves()) == 2, timeout=1000)
