import pandas as pd
import numpy as np

def run_wafer_data_cleaning():
    print("Executing factory shift-end data export...")
    np.random.seed(42)
    data = {
        'wafer_id': ['WAF_SI_09B'] * 50,
        'die_id': range(100, 150),
        'responsivity_AW': np.random.normal(0.65, 0.08, 50),
        'dark_current_nA': np.random.normal(5.0, 1.2, 50),
        'test_status': ['COMPLETE'] * 47 + ['INSTR_TIMEOUT', 'PROBE_DROP', 'COMPLETE']
    }
    df = pd.DataFrame(data)
    df_clean = df[df['test_status'] == 'COMPLETE'].copy()
    df_clean['passed_limits'] = (df_clean['responsivity_AW'] >= 0.55) & (df_clean['dark_current_nA'] <= 7.0)
    
    # Export report formats
    df_clean.to_csv("cleaned_wafer_production_report.csv", index=False)
    print(" -> Data report successfully exported to CSV.")

if __name__ == "__main__":
    run_wafer_data_cleaning()