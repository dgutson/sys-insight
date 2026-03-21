#!/usr/bin/env python3

from __future__ import annotations

import argparse
import time

import matplotlib.pyplot as plt

from sys_insight.providers import MetricProvider, CPUPerProcessProvider, MemPerProcessProvider
from sys_insight.sampler import Sampler
from sys_insight.renderer import StackedRenderer

# ---------- Types ----------

type PID = int
type MetricValue = float
type TimeSeries = list[float]
type Label = str

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
        renderer.draw(plot)
        time.sleep(args.interval)
