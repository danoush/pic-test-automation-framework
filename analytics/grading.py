"""Pass/fail grading of measured sweeps against limits.

This is analysis code: it works on SweepResult data and never touches hardware.
Limits arrive as arguments (ultimately from config), never as constants here.
"""

from dataclasses import dataclass

import numpy as np  # you will need it for the body

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
        ValueError: if no sweep points fall inside the band. Never pass a
            part you didn't measure.
    """
    passed = None
    mask = (result.frequency_hz >= band_hz[0]) & (result.frequency_hz <= band_hz[1])
    freq_arr = result.frequency_hz[mask]
    if freq_arr is None or freq_arr.size == 0:
        raise ValueError("Invalid frequency selection.")
    measured_db = -20 * np.log10(np.abs(result.s21[mask]))
    error = measured_db - nominal_db
    tolerance_db = 0.1
    worst_error_idx = np.argmax(np.abs(error))
    worst_error_db = error[worst_error_idx]
    #if worst_error_db >= tolerance_db:
    #    passed = False
    #else:
    #    passed = True
    if np.all(np.abs(error) <= tolerance_db):
        passed = True
    else:
        passed = False
    worst_frequency_hz = freq_arr[worst_error_idx]
    return Grade (passed=passed, 
                  worst_error_db=worst_error_db, 
                  worst_frequency_hz=worst_frequency_hz)
