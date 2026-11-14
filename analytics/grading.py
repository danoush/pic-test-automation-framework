"""Pass/fail grading of measured sweeps against limits.

This is analysis code: it works on SweepResult data and never touches hardware.
Limits arrive as arguments (ultimately from config), never as constants here.
"""

from dataclasses import dataclass

import numpy as np

from core.vna import SweepResult


@dataclass(frozen=True)
class Grade:
    """The outcome of grading one sweep.

    Attributes:
        passed: True if every point in the band is within tolerance.
        worst_error_db: The error with the largest magnitude, sign kept:
            measured attenuation minus nominal. Negative means less loss
            than the label says.
        worst_frequency_hz: The frequency where that worst error occurs.
    """

    passed: bool
    worst_error_db: float
    worst_frequency_hz: float


def grade_attenuation(
    result: SweepResult,
    nominal_db: float,
    tolerance_db: float,
    band_hz: tuple[float, float],
) -> Grade:
    """Grade an attenuator's S21 against nominal ± tolerance across a band.

    Attenuation is the loss as a positive number: -20 * log10(|S21|).
    A 3 dB pad should measure 3.0, not -3.0.

    Args:
        result: The measured sweep.
        nominal_db: The attenuation printed on the part, e.g. 3.0.
        tolerance_db: The allowed deviation either way, e.g. 0.1.
        band_hz: (low, high) in Hz, both ends included. Points outside the
            band are ignored.

    Returns:
        A Grade. It passes only if |error| <= tolerance_db at every point
        in the band.

    Raises:
        ValueError: if band extends beyond the sweep (on either side).
        ValueError: if no sweep points fall inside the band. Never pass a
            part you didn't measure.
    """
    band_min = band_hz[0]
    band_max = band_hz[1]
    sweep_min = result.frequency_hz[0]
    sweep_max = result.frequency_hz[-1]
    if band_min < sweep_min or band_max > sweep_max:
        raise ValueError(
            f"Band {band_min:g} to {band_max:g} Hz extends past the sweep ({sweep_min} to {sweep_max} hz)."
        )
    mask = (result.frequency_hz >= band_min) & (result.frequency_hz <= band_max)
    freqs_hz = result.frequency_hz[mask]
    if freqs_hz.size == 0:
        raise ValueError(
            f"Band {band_min:g} to {band_max:g} Hz contains no sampled frequencies."
        )
    measured_db = -20 * np.log10(np.abs(result.s21[mask]))
    error = measured_db - nominal_db
    worst_error_idx = np.argmax(np.abs(error))
    worst_error_db = error[worst_error_idx]
    passed = bool(np.all(np.abs(error) <= tolerance_db))
    worst_frequency_hz = freqs_hz[worst_error_idx]
    return Grade(
        passed=passed,
        worst_error_db=worst_error_db,
        worst_frequency_hz=worst_frequency_hz,
    )
