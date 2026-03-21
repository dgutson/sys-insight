from __future__ import annotations

from collections import deque

from sys_insight.models import MetricSample, PID, PlotData
from sys_insight.providers import ProcMeta, MetricProvider


class Sampler:
    def __init__(self, provider: MetricProvider, maxlen: int) -> None:
        self.provider = provider
        self.buffer: deque[MetricSample] = deque(maxlen=maxlen)

    def tick(self) -> None:
        self.buffer.append(self.provider.read())

    def _stable_top(self, top_n: int) -> list[PID]:
        acc: dict[PID, float] = {}

        for sample in self.buffer:
            for pid, v in sample.values.items():
                acc[pid] = acc.get(pid, 0.0) + v

        return [
            pid
            for pid, _ in sorted(acc.items(), key=lambda x: x[1], reverse=True)[:top_n]
        ]

    def series(self, top_n: int) -> PlotData:
        if not self.buffer:
            return PlotData([], [])

        top = self._stable_top(top_n)

        labels = [f"{pid} ({ProcMeta.get_comm(pid)})" for pid in top] + ["other"]

        data: dict[PID | str, list[float]] = {pid: [] for pid in top}
        data["other"] = []

        for sample in self.buffer:
            other = 0.0

            for pid, v in sample.values.items():
                if pid in data:
                    data[pid].append(v)
                else:
                    other += v

            for pid in top:
                if len(data[pid]) < len(data["other"]) + 1:
                    data[pid].append(0.0)

            data["other"].append(other)

        series = [data[pid] for pid in top] + [data["other"]]

        return PlotData(labels, series)
