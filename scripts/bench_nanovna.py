"""
Frequency sweep through NanoVNA using measure(start_hz, stop_hz, points). Tracks performance via perf_counter().
Outputs S21 in db (next to associated frequencies), calibration data, and IF bandwidth. 
"""

import numpy as np
from time import perf_counter
from core.nanovna import NanoVNA


with NanoVNA("COM3") as vna:
    print(vna.identify())
    start = perf_counter()
    result = vna.measure(50e3, 900e6, 101)
    end = perf_counter()
    print(f"Measurement took {end - start:.3f} seconds.")
    
    # Calculate S21 in dB (Insertion Loss / Attenuation)
    s21_db = 20 * np.log10(np.abs(result.s21))

    # Specify S21 in dB at 0.05 MHz, 450.025 MHz, and 900 MHz (given above, just isolated here)
    # Automatically pick 5 evenly-spaced sample points across the 101-point sweep
    num_samples = 5
    indices = np.linspace(0, len(result.frequency_hz) - 1, num_samples, dtype=int)
    s21_db_samples = s21_db[indices]
    
    # Calculate S11 in dB (Reflection / Return Loss)
    s11_db = 20 * np.log10(np.abs(result.s11))

    # Find the maximum (worst) S11 value across the sweep
    # (Since they are negative numbers, max() finds the number closest to 0 / least negative)
    worst_s11 = np.max(s11_db)

    print("S21 in dB:")
    for freq, db in zip(result.frequency_hz, s21_db):
        print(f"{freq / 1e6:8.3f} MHz: {db:.2f} dB")
    print("\nS21 samples at target frequencies:")
    for freq, val in zip(result.frequency_hz[indices], s21_db_samples):
        print(f"{freq / 1e6:8.3f} MHz: {val:.2f} dB")
    print(f"\nWorst S11 (Reflection):\n{worst_s11:.2f} dB")
    print("\nCalibration data:", vna._query("cal"))
    print("\nIF Bandwidth:", vna._query("bandwidth"))

    vna._query("resume")
