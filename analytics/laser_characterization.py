import pandas as pd
import numpy as np

# needs cleaning up, comments in particular might be whack. np.polyfit can be replaced with Polynomial.fit

def analyze_laser_li_curve():
    print("--- AUTOMATED INP LASER PARAMETRIC CHARACTERIZATION ---")
    
    # 1. Simulate a current ramp sweep (0 mA to 50 mA)
    current_ma = np.linspace(0, 50, 50)
    
    # Simulate a laser profile with a threshold at exactly 15 mA
    # Below 15mA, power is near zero (spontaneous leakage noise)
    # Above 15mA, power scales linearly with a slope efficiency of 0.4 mW/mA
    threshold_nominal = 15.0
    slope_nominal = 0.4
    
    power_mw = []
    constant_noise_floor = np.random.normal(0.01, 0.005, size=current_ma.shape) # Background noise floor is present across all current levels
    stimulated_power = (current_ma - threshold_nominal) * slope_nominal # Pure stimulated lasing power only calculates values above the threshold point
    lasing_signal = np.where(current_ma < threshold_nominal, 0.0, stimulated_power) # Add them together and clip physical power at absolute zero
    power_mw = np.maximum(0, lasing_signal + constant_noise_floor)

    df = pd.DataFrame({'Current_mA': current_ma, 'Power_mW': power_mw})

    # Pure Vectorized L-I Data Generation
current_ma = np.linspace(0, 50, 50)


    print("\n--- STEP 1: AUTOMATED THRESHOLD CURRENT DETECTION ---")
    # In HVM, we locate the threshold by calculating the second derivative (d^2P/dI^2)
    # The peak of the second derivative indicates the sharpest change in curve velocity (lasing onset)
    df['dP'] = np.gradient(df['Power_mW'], df['Current_mA'])
    df['d2P'] = np.gradient(df['dP'], df['Current_mA'])
    
    threshold_idx = df['d2P'].idxmax()
    calculated_ith = df.loc[threshold_idx, 'Current_mA']
    print(f"Detected Laser Threshold Current (Ith): {calculated_ith:.2f} mA")
    
    print("\n--- STEP 2: CALCULATING SLOPE EFFICIENCY ---")
    # Isolate the linear lasing region (well above the calculated threshold to avoid knee noise)
    lasing_region = df[df['Current_mA'] > (calculated_ith + 5.0)]
    
    # Use a linear regression fit (y = mx + b) on the lasing region to find the slope
    slope, intercept = np.polyfit(lasing_region['Current_mA'], lasing_region['Power_mW'], 1)
    print(f"Calculated Slope Efficiency (eta): {slope:.4f} mW/mA")
    
    print("\n--- STEP 3: QUALITY CONTROL VERDICT ---")
    # Standard HVM screening window limits
    if calculated_ith <= 18.0 and slope >= 0.35:
        print("VERDICT: PASS (Core InP light source meets downstream transceiver module specs.)")
    else:
        print("VERDICT: FAIL (Parametric outlier. Scrape device from wafer map layout.)")

if __name__ == "__main__":
    analyze_laser_li_curve()
