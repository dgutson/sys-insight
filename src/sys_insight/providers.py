from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import override

from sys_insight.models import MetricSample, PID


class MetricProvider(ABC):
    @abstractmethod
    def read(self) -> MetricSample:
        ...


class ProcMeta:
    @staticmethod
    def get_comm(pid: PID) -> str:
        try:
            # pylint: disable=unspecified-encoding
            with open(f"/proc/{pid}/comm") as f:
                return f.read().strip()

        # pylint: disable=broad-exception-caught
        except Exception:
            return "?"


class CPUPerProcessProvider(MetricProvider):
    def __init__(self) -> None:
        self._prev: dict[PID, int] = {}

    @staticmethod
    def _read_stat(pid: PID) -> int | None:
        try:
            # pylint: disable=unspecified-encoding
            with open(f"/proc/{pid}/stat") as f:
                parts = f.read().split()
            return int(parts[13]) + int(parts[14])

        # pylint: disable=broad-exception-caught
        except Exception:
            return None

    @override
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
            if prev is None:
                continue

            d = val - prev
            if d > 0:
                deltas[pid] = float(d)

        self._prev = curr

        total = sum(deltas.values()) or 1.0

        return MetricSample(
            {pid: v / total for pid, v in deltas.items()}
        )


class MemPerProcessProvider(MetricProvider):
    @staticmethod
    def _read_rss(pid: PID) -> int | None:
        try:
            # pylint: disable=unspecified-encoding
            with open(f"/proc/{pid}/statm") as f:
                parts = f.read().split()
            return int(parts[1])

        # pylint: disable=broad-exception-caught
        except Exception:
            return None

    @override
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
            {pid: v / total for pid, v in values.items()}
        )
