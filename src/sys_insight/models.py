from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple, TypeAlias

type PID = int
MetricValue: TypeAlias = float
type TimeSeries = list[float]
type Label = str


@dataclass(frozen=True)
class MetricSample:
    values: dict[PID, MetricValue]


class PlotData(NamedTuple):
    labels: list[Label]
    series: list[TimeSeries]
