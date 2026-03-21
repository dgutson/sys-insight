from __future__ import annotations

import matplotlib.pyplot as plt

from sys_insight.models import PlotData


class StackedRenderer:
    def __init__(self) -> None:
        self.fig, self.ax = plt.subplots()

    def draw(self, plot: PlotData) -> None:
        self.ax.clear()

        if plot.series:
            self.ax.stackplot(
                range(len(plot.series[0])),
                plot.series,
                labels=plot.labels,
            )

        self.ax.set_ylim(0, 1)
        self.ax.legend(loc="upper left", fontsize=6)

        plt.pause(0.01)
