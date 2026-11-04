"""The measurement contract that every VNA driver implements.

A driver's only job is to talk to its instrument and hand back raw data:
frequencies plus complex S-parameters. Conversions (dB, phase, VSWR) and
pass/fail decisions happen in analysis code, never inside a driver.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


# frozen=True: fields can't be reassigned after creation (result.s21 = ... raises).
# eq=False: skip the auto-generated ==, which would compare NumPy arrays
# element by element and then raise "truth value of an array is ambiguous".
@dataclass(frozen=True, eq=False)
class SweepResult:
    """One frequency sweep: complex S-parameters at each frequency point.

    Only S11 and S21 are here because that's all a NanoVNA can measure:
    port 1 transmits and receives, port 2 only receives. Getting S22 and S12
    means physically turning the device under test around.

    Attributes:
        frequency_hz: Sweep frequencies in Hz, shape (N,).
        s11: Complex reflection coefficient at port 1, shape (N,).
        s21: Complex transmission from port 1 to port 2, shape (N,).
    """

    frequency_hz: np.ndarray
    s11: np.ndarray
    s21: np.ndarray

    def __post_init__(self) -> None:
        # Runs automatically right after the generated __init__.
        n = len(self.frequency_hz)
        if len(self.s11) != n or len(self.s21) != n:
            raise ValueError(
                f"length mismatch: {n} frequencies, {len(self.s11)} S11 values, "
                f"{len(self.s21)} S21 values"
            )


class VNA(ABC):
    """Interface for vector network analyzers.

    Use a driver as a context manager so the connection is always released,
    even when a measurement raises an exception:

        with NanoVNA("COM3") as vna:
            result = vna.measure(50e3, 900e6, 101)
    """

    @abstractmethod
    def connect(self) -> None:
        """Open the connection; raise ConnectionError if the instrument doesn't answer."""

    @abstractmethod
    def close(self) -> None:
        """Release the connection. Safe to call twice, or without connecting first."""

    @abstractmethod
    def identify(self) -> str:
        """Return an identification string, such as the firmware version."""

    @abstractmethod
    def measure(self, start_hz: float, stop_hz: float, points: int) -> SweepResult:
        """Run one sweep now and return its data.

        Every call triggers a new measurement. It must never return data that
        was captured before the call.
        """

    def __enter__(self) -> "VNA":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # Returning None (falsy) lets any exception from the with-block propagate.
        self.close()
