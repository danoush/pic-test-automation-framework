"""Tests for the measurement contract in core/vna.py."""

import numpy as np
import pytest

from core.vna import VNA, SweepResult


def test_sweep_result_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        SweepResult(
            frequency_hz=np.array([1e6, 2e6, 3e6]),
            s11=np.array([1 + 0j, 1 + 0j, 1 + 0j]),
            s21=np.array([0j, 0j]),  # one value short
        )


def test_vna_cannot_be_used_without_implementing_the_contract():
    class HalfDone(VNA):
        def connect(self):
            pass

    with pytest.raises(TypeError):
        HalfDone()  # close, identify and measure are still abstract
