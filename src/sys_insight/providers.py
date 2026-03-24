from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import override

from sys_insight.models import MetricValue, MetricSample, PID


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


class ProcMetricProvider(MetricProvider):
    @abstractmethod
    def _read_proc_value(self, pid: PID) -> MetricValue | None:
        ...

    @override
    def read(self) -> MetricSample:
        values: dict[PID, MetricValue] = {}

        def _read_values() -> dict[PID, MetricValue]:
            for p in Path("/proc").iterdir():
                if not p.name.isdigit():
                    continue

                pid = int(p.name)
                value = self._read_proc_value(pid)
                if value is not None:
                    values[pid] = value
            return values

        values = _read_values()
        total = sum(values.values()) or 1.0

        return MetricSample(
            {pid: v / total for pid, v in values.items()}
        )

class ProcDeltaMetricProvider(ProcMetricProvider):
    @abstractmethod
    def _read_current_prov_value(self, pid: PID) -> MetricValue | None:
        ...

    def __init__(self) -> None:
        self.old_values: dict[PID, MetricValue | None] = {}

    @staticmethod
    def _ignore_negative(delta: MetricValue) -> MetricValue | None:
        return delta if delta > 0.0 else None

    @override
    def _read_proc_value(self, pid: PID) -> MetricValue | None:
        current = self._read_current_prov_value(pid)
        delta : MetricValue | None = None

        if current is not None:
            old = self.old_values.get(pid)
            if old is not None:
                delta = self._ignore_negative(current - old)
            # else: this means that there is no prev value. Wait until the second.

        self.old_values[pid] = current

        return delta


# Implementations:

class CPUPerProcessProvider(ProcDeltaMetricProvider):
    @override
    def _read_current_prov_value(self, pid: PID) -> MetricValue | None:
        try:
            # pylint: disable=unspecified-encoding
            with open(f"/proc/{pid}/stat") as f:
                parts = f.read().split()
            return MetricValue(parts[13]) + MetricValue(parts[14])

        # pylint: disable=broad-exception-caught
        except Exception:
            return None


class MemPerProcessProvider(ProcMetricProvider):
    @override
    def _read_proc_value(self, pid: PID) -> MetricValue | None:
        try:
            # pylint: disable=unspecified-encoding
            with open(f"/proc/{pid}/statm") as f:
                parts = f.read().split()
            return MetricValue(parts[1])

        # pylint: disable=broad-exception-caught
        except Exception:
            return None
