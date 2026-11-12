"""Tests for analytics/grading.py.

Most tests build a synthetic sweep with a known attenuation at every point.
The last two use your real pad measurements (the 5 sample points).
Run with:  pytest tests/test_grading.py -x
"""

import numpy as np
import pytest

from analytics.grading import grade_attenuation
from core.vna import SweepResult

FREQS = np.linspace(50e3, 900e6, 101)  # the same 101 points as your sweeps


def make_sweep(attenuation_db, freqs=FREQS):
    """A SweepResult whose S21 has the given attenuation (in dB) at each point."""
    attenuation_db = np.asarray(attenuation_db, dtype=float)
    s21 = 10 ** (-attenuation_db / 20) + 0j  # 3 dB of loss -> |S21| = 0.708
    return SweepResult(frequency_hz=np.asarray(freqs, dtype=float), s11=np.zeros_like(s21), s21=s21)


def flat(attenuation_db):
    """A sweep with the same attenuation at all 101 points."""
    return make_sweep(np.full(FREQS.shape, attenuation_db))


def test_pad_exactly_at_nominal_passes():
    grade = grade_attenuation(flat(3.0), nominal_db=3.0, tolerance_db=0.1, band_hz=(50e3, 900e6))
    assert grade.passed
    assert grade.worst_error_db == pytest.approx(0.0, abs=1e-9)


def test_small_errors_within_tolerance_pass():
    attenuation = np.full(FREQS.shape, 3.0)
    attenuation[::2] = 3.09   # every other point 0.09 dB heavy
    attenuation[1::2] = 2.92  # the rest 0.08 dB light
    grade = grade_attenuation(make_sweep(attenuation), 3.0, 0.1, (50e3, 900e6))
    assert grade.passed


def test_too_little_loss_fails_too():
    # Tolerance applies both ways: a pad that reads light is out of spec as well.
    grade = grade_attenuation(flat(2.85), 3.0, 0.1, (50e3, 900e6))
    assert not grade.passed
    assert grade.worst_error_db == pytest.approx(-0.15)


def test_reports_worst_error_and_its_frequency():
    attenuation = np.full(FREQS.shape, 3.0)
    attenuation[40] = 3.25
    grade = grade_attenuation(make_sweep(attenuation), 3.0, 0.1, (50e3, 900e6))
    assert not grade.passed
    assert grade.worst_error_db == pytest.approx(0.25)
    assert grade.worst_frequency_hz == FREQS[40]


def test_largest_magnitude_wins_and_keeps_its_sign():
    # -0.30 dB beats +0.15 dB: worst means farthest from nominal, either way.
    attenuation = np.full(FREQS.shape, 3.0)
    attenuation[10] = 2.70
    attenuation[20] = 3.15
    grade = grade_attenuation(make_sweep(attenuation), 3.0, 0.1, (50e3, 900e6))
    assert not grade.passed
    assert grade.worst_error_db == pytest.approx(-0.30)
    assert grade.worst_frequency_hz == FREQS[10]


def test_points_outside_the_band_are_ignored():
    attenuation = np.full(FREQS.shape, 3.0)
    attenuation[100] = 3.5  # bad only at 900 MHz
    grade = grade_attenuation(make_sweep(attenuation), 3.0, 0.1, (50e3, 675.013e6))
    assert grade.passed


def test_band_edges_are_included():
    attenuation = np.full(FREQS.shape, 3.0)
    attenuation[50] = 3.5  # exactly on the band's upper edge
    grade = grade_attenuation(make_sweep(attenuation), 3.0, 0.1, (FREQS[10], FREQS[50]))
    assert not grade.passed
    assert grade.worst_frequency_hz == FREQS[50]


def test_empty_band_raises():
    with pytest.raises(ValueError):
        grade_attenuation(flat(3.0), 3.0, 0.1, (1e9, 2e9))  # above the whole sweep


# ---------- your real measurements ----------

SAMPLE_FREQS = np.array([50e3, 225.037e6, 450.025e6, 675.013e6, 900e6])


def measured(s21_db):
    """A 5-point sweep built from S21 readings in dB (negative numbers)."""
    return make_sweep(-np.asarray(s21_db), freqs=SAMPLE_FREQS)


def test_your_3db_pad_fails_its_spec():
    # Nov 10, NanoVNA barrel, run 1
    pad = measured([-2.74, -2.78, -2.81, -2.80, -2.51])
    grade = grade_attenuation(pad, 3.0, 0.1, (50e3, 675.013e6))
    assert not grade.passed
    assert grade.worst_error_db == pytest.approx(-0.26)
    assert grade.worst_frequency_hz == 50e3


def test_your_10db_pad_passes_up_to_450_mhz():
    # Nov 8, first calibration
    pad = measured([-9.91, -9.99, -9.95, -9.86, -9.39])
    grade = grade_attenuation(pad, 10.0, 0.1, (50e3, 450.025e6))
    assert grade.passed
    assert grade.worst_error_db == pytest.approx(-0.09)
