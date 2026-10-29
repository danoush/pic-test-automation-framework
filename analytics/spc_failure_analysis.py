import sqlite3
import json
import os
import pandas as pd

# can use pathlib instead (more modern approach)

def load_factory_specifications():
    """Dynamically reads the decoupled hardware thresholds from the JSON configuration."""
    # Resolve file path relative to this script's position to avoid terminal execution bugs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "..", "config", "factory_settings.json")
    
    with open(config_path, "r") as file:
        return json.load(file)

def execute_spc_yield_audit():
    print("--- HVM RUNTIME STATISTICAL PROCESS CONTROL (SPC) AUDIT ---")
    
    # 1. Ingest our decoupled configuration variables
    specs = load_factory_specifications()
    moving_window = specs["spc_rules"]["moving_average_window"]
    alert_threshold = specs["spc_rules"]["critical_yield_alert_percent"]
    
    # 2. Extract historical production data from the relational database file
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hvm_test_factory.db")
    if not os.path.exists(db_path):
        print(f"Aborting Audit: Database file not found at {db_path}. Run the execution engine first.")
        return
        
    conn = sqlite3.connect(db_path)
    
    # Read the data straight into a Pandas DataFrame for heavy matrix parsing
    df = pd.read_sql_query("SELECT id, timestamp, die_number, status FROM die_test_results ORDER BY id ASC", conn)
    conn.close()
    
    if len(df) == 0:
        print("Database is empty. No manufacturing parameters available to analyze.")
        return
        
    # 3. Process vectorized yield metrics
    # Convert text strings ('PASS'/'FAIL') into binary numeric scalars (1/0) so we can run rolling statistics
    df['binary_status'] = df['status'].apply(lambda x: 1 if x == 'PASS' else 0)
    
    # Calculate a rolling moving-average yield across our window constraint (multiplied by 100 for percent)
    df['rolling_yield_%'] = df['binary_status'].rolling(window=moving_window, min_periods=1).mean() * 100
    
    print(f"Successfully processed {len(df)} historical die test positions.")
    print("\n--- RECENT RUNTIME PRODUCTION METRICS ---")
    print(df[['id', 'die_number', 'status', 'rolling_yield_%']].tail(7))
    
    print("\n--- EVALUATING SPC QUALITY RULES ---")
    # Fetch the latest computed rolling yield value from the line
    current_rolling_yield = df['rolling_yield_%'].iloc[-1]
    latest_die = df['die_number'].iloc[-1]
    
    # Check if our process yield crosses into our critical limit threshold window
    if current_rolling_yield < alert_threshold:
        print(f"⚠️  CRITICAL QUALITY ALERT TRIGGERED AT DIE #{latest_die}!")
        print(f" -> Current Rolling Line Yield: {current_rolling_yield:.2f}%")
        print(f" -> Configured Quality Floor Limit : {alert_threshold:.2f}%")
        print("⚠️  ACTION REQUIRED: Rolling average indicates a rapid drop in line yield.")
        print("    Flagged issues: Potential mechanical probe degradation or physical lithography layer shifting.")
    else:
        print(f"SUCCESS: Rolling line yield ({current_rolling_yield:.2f}%) is well within safe limits (>{alert_threshold}%).")
        print("         Manufacturing process is currently stable and running efficiently.")

if __name__ == "__main__":
    execute_spc_yield_audit()