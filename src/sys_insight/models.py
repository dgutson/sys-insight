from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

type PID = int
type MetricValue = float
type TimeSeries = list[float]
type Label = str


@dataclass(frozen=True)
class MetricSample:
    values: dict[PID, MetricValue]


class PlotData(NamedTuple):
    labels: list[Label]
    series: list[TimeSeries]
