import copy

import numpy as np
from silx.gui.plot import Plot1D
from silx.gui.plot.actions import PlotAction


class DerivativeAction(PlotAction):
    """
    Plot action for computing and displaying the first derivative of all curves when checked.
    """

    def __init__(self, plot: Plot1D, parent=None):
        super().__init__(
            plot,
            icon="math-derive",
            text="Derivative",
            tooltip="Show derivates of all curves on the plot",
            triggered=self.derivate_action,
            checkable=True,
            parent=parent,
        )

        self._displaying = False

        self._legend_previously_hidden = False
        self._current_plotted_derivatives = dict()

        self.plot.sigContentChanged.connect(self.update_derivative)

    def update_derivative(self, action, kind, legend):
        if not self._displaying or legend not in self._current_plotted_derivatives:
            return

        if action == "remove":
            self.plot.remove(self._current_plotted_derivatives[legend])
            return

        original_curve = self.plot.getCurve(legend)
        if original_curve is None:
            return

        x = original_curve.getXData()
        y = original_curve.getYData()
        info = original_curve.getInfo()

        if info is None:
            info = {}

        derivative = np.gradient(y, x, edge_order=2)

        derivative_curve_name = self._current_plotted_derivatives[legend]
        derivative_curve = self.plot.getCurve(derivative_curve_name)
        if derivative_curve is not None:
            derivative_curve.setData(x, derivative)
        else:
            self.plot.addCurve(
                x,
                derivative,
                legend=derivative_curve_name,
                info=info,
                linestyle="--",
                yaxis="right",
            )

    def derivate_action(self, checked=False):
        self._displaying = checked

        all_curves = self.plot.getAllCurves()

        if not checked:
            current_plotted_derivatives = copy.copy(self._current_plotted_derivatives)
            self._current_plotted_derivatives.clear()

            for derivative_curve_name in current_plotted_derivatives.values():
                self.plot.remove(derivative_curve_name)

            if not self._legend_previously_hidden:
                self.plot.getLegendsDockWidget().hide()

            return

        for curve in all_curves:
            legend = curve.getLegend()

            derivative_legend = "Derivative of " + legend
            self._current_plotted_derivatives[legend] = derivative_legend
            self.update_derivative("add", "curve", legend)

            legend_widget = self.plot.getLegendsDockWidget()

            self._legend_previously_hidden = legend_widget.isVisible()
            legend_widget.show()
