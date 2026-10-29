import sys
import os
import time
import json

# Ensure Python can find the root directory modules if run directly from within the pipelines folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.vna_drivers import KeysightVNA, AnritsuVNA
from pipelines.data_logger import initialize_production_database

def run_automated_wafer_probe_line(vna_hardware_driver):
    """
    Main HVM Test Sequence execution engine. 
    Accepts ANY valid VNA driver that conforms to our core AbstractVNA class design.
    """
    print(f"\n=======================================================")
    print(f"INITIALIZING AUTOMATED WAFER PROBE SYSTEM ENGINE")
    print(f"=======================================================")
    
    # 1. Connect to our localized relational database
    db_conn = initialize_production_database()
    db_cursor = db_conn.cursor()


    try:
        # 2. Boot up instrument hardware interface layer
        is_ready = vna_hardware_driver.connect()
        if not is_ready:
            print("CRITICAL: Hardware connection timed out. Aborting lot run.")
            return
            
        # Optimize instrument sweep parameters for factory throughput
        vna_hardware_driver.set_if_bandwidth(20000) # 20 kHz HVM filter standard
        
        target_wafer = "WAF_SI_09B"
        print(f"\nStarting automated step-and-repeat wafer sweep for Lot: {target_wafer}")
        
        # 3. Simulate high-volume die indexing over physical coordinates
        for die_number in range(101, 106):
            time.sleep(0.1) # Simulate mechanical micro-positioning stage travel time
            
            # Execute the measurement sweep array via the HAL driver
            s21_trace_data = vna_hardware_driver.capture_s21_trace()
            peak_power = max(s21_trace_data)
            
            # Parametric pass/fail grading limits step
            with open("config/factory_settings.json", "r") as f:
                specs = json.load(f)
            s21_limit = specs["pass_fail_thresholds"]["min_s21_peak_db"]
            grading_verdict = "PASS" if peak_power >= s21_limit else "FAIL"
            
            # Write metrics into relational storage via safe parameterized queries
            db_cursor.execute("""
                INSERT INTO die_test_results (wafer_id, die_number, peak_power_dbm, status)
                VALUES (?, ?, ?, ?)
            """, (target_wafer, die_number, peak_power, grading_verdict))
            
            print(f" -> Positioned at Die #{die_number} | Measured S21 Max: {peak_power:.2f} dB | Status: {grading_verdict}")
            
        # Permanently save data rows
        db_conn.commit()
        print("\nWafer production dataset cleanly uploaded to database.")
        
    except Exception as err:
        print(f"Pipeline Execution Aborted: {err}")
        
    finally:
        db_conn.close()
        print("Relational database link closed safely.")

if __name__ == "__main__":
    # Test Scenario A: Execute line using Keysight hardware configuration
    keysight_station_hardware = KeysightVNA(resource_address="GPIB0::22::INSTR")
    run_automated_wafer_probe_line(keysight_station_hardware)
    
    # Test Scenario B: Execute identical sequence using alternative Anritsu gear
    anritsu_station_hardware = AnritsuVNA(resource_address="TCPIP0::192.168.1.50::INSTR")
    run_automated_wafer_probe_line(anritsu_station_hardware)
