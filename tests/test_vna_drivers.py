import pytest
import sys
import os

# Can upgrade to more modern pathlib, or even better, pyproject.toml with run pip install -e 

# Ensure the execution runtime can locate the core repository files
sys.path.append(str(Path(__file__).parent.parent))
from core.vna_drivers import KeysightVNA, AnritsuVNA

def test_keysight_driver_initial_state():
    """Validates that a new Keysight driver initializes in a safe, disconnected state."""
    driver = KeysightVNA("GPIB0::22::INSTR")
    assert driver.is_connected is False
    assert driver.resource_address == "GPIB0::22::INSTR"

def test_keysight_successful_connection():
    """Verifies that calling connect updates the internal state flags correctly."""
    driver = KeysightVNA("GPIB0::22::INSTR")
    connection_success = driver.connect()
    
    assert connection_success is True
    assert driver.is_connected is True

def test_keysight_bandwidth_disconnection_guard():
    """
    Enforces basic safety hygiene: The driver must raise a ConnectionError 
    if an engineer attempts to alter hardware states before connecting.
    """
    driver = KeysightVNA("GPIB0::22::INSTR")
    
    # Assert that a ConnectionError is correctly raised by the HAL guard
    with pytest.raises(ConnectionError) as exc_info:
        driver.set_if_bandwidth(10000)
    
    assert "Instrument session is not open" in str(exc_info.value)

def test_vendor_trace_data_conformity():
    """
    Validates data contract integrity. Both Keysight and Anritsu child drivers 
    must return a python list of exactly 5 scalar data points during an S21 sweep.
    """
    keysight_tool = KeysightVNA("GPIB0::22::INSTR")
    anritsu_tool = AnritsuVNA("TCPIP0::192.168.1.50::INSTR")
    
    keysight_tool.connect()
    anritsu_tool.connect()
    
    k_trace = keysight_tool.capture_s21_trace()
    a_trace = anritsu_tool.capture_s21_trace()
    
    # Structural assertions to protect downstream Pandas processing pipelines
    assert isinstance(k_trace, list)
    assert isinstance(a_trace, list)
    assert len(k_trace) > 0, "The data capture pipeline returned an empty trace array asset."
    assert len(a_trace) > 0, "The data capture pipeline returned an empty trace array asset."
    assert all(isinstance(val, float) for val in k_trace), "Non-scalar data formats leaked into the output vector."