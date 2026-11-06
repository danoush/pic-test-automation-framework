"""
Inside with NanoVNA("COM3") as vna:, have the script:

print identify().
time measure(50e3, 900e6, 101) with time.perf_counter(). Test time per device is the headline metric in high-volume manufacturing.
convert S21 to dB in the script, not the driver, then plot or print it. You should see the 300 MHz step, this time with real frequencies.
print vna._query("cal") and vna._query("bandwidth"). The underscore means internal, but calling it from a bench script is fine.
run again with port 1 connected to port 2 through both cables and the barrel. S21 should be near 0 dB, a few tenths low from cable loss.
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
    
    s21_db = 20 * np.log10(np.abs(result.s21))
    print("S21 in dB:\n", s21_db)
    
    print("Calibration data:", vna._query("cal"))
    print("IF Bandwidth:", vna._query("bandwidth"))