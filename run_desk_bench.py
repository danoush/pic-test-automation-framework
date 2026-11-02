import sys
import os

# Align local workspace environment directory path trees
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.nanovna_driver import PhysicalNanoVNA
from pipelines.execution_engine import run_automated_wafer_probe_line

def execute_live_desk_run():
    print("=======================================================")
    print("LAUNCHING LIVE COUPLING SWEEP INTERFACE VIA COM3")
    print("=======================================================")
    
    # 1. Initialize our physical serial driver targeting your active port
    # Substitute with your validated Windows hardware resource name
    hardware_target_port = "COM3"
    
    vna_bench_device = PhysicalNanoVNA(resource_address=hardware_target_port)
    
    try:
        # 2. Feed your real device directly into your production line database engine
        # The engine treats it uniformly because it conforms to our AbstractVNA parent blueprint!
        run_automated_wafer_probe_line(vna_bench_device)
        
    except Exception as e:
        print(f"Execution failed on bench run sequence: {e}")
        
    finally:
        # 3. Clean up the physical operating system resource port session locks
        vna_bench_device.close()
        print("\nBench test run complete.")

if __name__ == "__main__":
    execute_live_desk_run()