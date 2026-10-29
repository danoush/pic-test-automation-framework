import pandas as pd
import numpy as np

def calculate_gage_rr():
    print("--- AUTOMATED SEMICONDUCTOR GAGE R&R METRIC ANALYSIS ---")
    np.random.seed(10)
    dies = np.repeat([1, 2, 3], 6)
    shifts = np.tile(np.repeat(['Shift_1', 'Shift_2'], 3), 3)
    trials = np.tile([1, 2, 3], 6)
    base_die_power = {1: -0.2, 2: -0.5, 3: -1.1}
    measured_power = [base_die_power[d] for d in dies]
    measured_power += np.random.normal(0, 0.02, 18)
    
    for i, shift in enumerate(shifts):
        if shift == 'Shift_2':
            measured_power[i] += 0.07 

    df = pd.DataFrame({'Die_ID': dies, 'Shift': shifts, 'Trial': trials, 'Peak_Power_dBm': measured_power})
    trial_ranges = df.groupby(['Die_ID', 'Shift'])['Peak_Power_dBm'].agg(lambda x: x.max() - x.min())
    R_bar = trial_ranges.mean()
    EV = R_bar / 1.693
    
    shift_means = df.groupby('Shift')['Peak_Power_dBm'].mean()
    X_bar_diff = abs(shift_means['Shift_1'] - shift_means['Shift_2'])
    raw_av_sq = (X_bar_diff / 1.128)**2 - (EV**2 / 9)
    AV = np.sqrt(max(0, raw_av_sq))
    
    GRR = np.sqrt(EV**2 + AV**2)
    print(f"Calculated Total Gage R&R Measurement Noise: {GRR:.4f} dB")

if __name__ == "__main__":
    calculate_gage_rr()