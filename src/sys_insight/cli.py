#!/usr/bin/env python3

from __future__ import annotations
from typing import NamedTuple

import argparse
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


# ---------- Types ----------

type PID = int
type MetricValue = float
type TimeSeries = list[float]
type Label = str

class PlotData(NamedTuple):
    labels: list[Label]
    series: list[TimeSeries]

@dataclass(frozen=True)
class MetricSample:
    values: dict[PID, MetricValue]

class ProcMeta:
    @staticmethod
    def get_comm(pid: PID) -> str:
        try:
            with open(f"/proc/{pid}/comm") as f:
                return f.read().strip()
        except Exception:
            return "?"

# ---------- Provider ----------

class MetricProvider(ABC):
    @abstractmethod
    def read(self) -> MetricSample:
        pass


# ---------- CPU per-process ----------

class CPUPerProcessProvider(MetricProvider):
    def __init__(self) -> None:
        self._prev: dict[PID, int] = {}

    @staticmethod
    def _read_stat(pid: PID) -> int | None:
        try:
            with open(f"/proc/{pid}/stat") as f:
                parts = f.read().split()
            return int(parts[13]) + int(parts[14])
        except Exception:
            return None

    def read(self) -> MetricSample:
        curr: dict[PID, int] = {}

        for p in Path("/proc").iterdir():
            if not p.name.isdigit():
                continue

            pid = int(p.name)
            val = self._read_stat(pid)
            if val is not None:
                curr[pid] = val

        deltas: dict[PID, float] = {}

        for pid, val in curr.items():
            prev = self._prev.get(pid)
            if prev is not None:
                d = val - prev
                if d > 0:
                    deltas[pid] = float(d)

        self._prev = curr

        total = sum(deltas.values()) or 1.0

        return MetricSample(
            values={pid: v / total for pid, v in deltas.items()}
        )


# ---------- Memory per-process ----------

class MemPerProcessProvider(MetricProvider):
    @staticmethod
    def _read_rss(pid: PID) -> int | None:
        try:
            with open(f"/proc/{pid}/statm") as f:
                parts = f.read().split()
            return int(parts[1])
        except Exception:
            return None

    def read(self) -> MetricSample:
        values: dict[PID, float] = {}

        for p in Path("/proc").iterdir():
            if not p.name.isdigit():
                continue

            pid = int(p.name)
            rss = self._read_rss(pid)
            if rss is not None:
                values[pid] = float(rss)

        total = sum(values.values()) or 1.0

        return MetricSample(
            values={pid: v / total for pid, v in values.items()}
        )


# ---------- Sampler ----------

class Sampler:
    def __init__(self, provider: MetricProvider, maxlen: int) -> None:
        self.provider = provider
        self.buffer: deque[MetricSample] = deque(maxlen=maxlen)

    def tick(self) -> None:
        self.buffer.append(self.provider.read())

    def stable_top(self, top_n: int) -> list[PID]:
        acc: dict[PID, float] = {}

        for sample in self.buffer:
            for pid, v in sample.values.items():
                acc[pid] = acc.get(pid, 0.0) + v

        return [
            pid
            for pid, _ in sorted(acc.items(), key=lambda x: x[1], reverse=True)[
                :top_n
            ]
        ]

    def series(self, top_n: int) -> PlotData:
        if not self.buffer:
            return PlotData([], [])

        top = self.stable_top(top_n)

        labels: list[Label] = []
        for pid in top:
            name = ProcMeta.get_comm(pid)
            labels.append(f"{pid} ({name})")

        labels.append("other")

        data: dict[PID | str, TimeSeries] = {pid: [] for pid in top}
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

        series: list[TimeSeries] = [
            data[pid] for pid in top
        ] + [data["other"]]

        return PlotData(labels, series)

# ---------- Renderer ----------

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
        #self.ax.set_title("Per-process usage (stable window)")

        plt.pause(0.01)


# ---------- CLI ----------

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--metric", choices=["cpu", "mem"], default="cpu")
    p.add_argument("-n", "--samples", type=int, default=60)
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--interval", type=float, default=1.0)
    args = p.parse_args()

    provider: MetricProvider = (
        CPUPerProcessProvider()
        if args.metric == "cpu"
        else MemPerProcessProvider()
    )

    sampler = Sampler(provider, args.samples)
    renderer = StackedRenderer()

    plt.ion()

    while plt.fignum_exists(renderer.fig.number):
        sampler.tick()
        plot = sampler.series(args.top)
        #labels, data = sampler.series(args.top)
        #renderer.draw(labels, data)
        renderer.draw(plot)
        time.sleep(args.interval)
