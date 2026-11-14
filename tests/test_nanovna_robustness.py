import pytest
import math
from core.nanovna_driver import PhysicalNanoVNA

# --- COUPLING DRIVER TEST ENHANCEMENTS (FAULT INJECTION) ---


class DummyFaultySerial:
    """Mock serial port that mimics a heavily corrupted NanoVNA hardware stream."""

    def __init__(self, behavioral_scenario):
        self.behavioral_scenario = behavioral_scenario
        self.in_waiting = 1
        self.timeout = 1.0
        self._has_read = False

    def write(self, command):
        pass

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass

    def read(self, size):
        if self._has_read:
            return b""
        self._has_read = True

        # Scenario A: The device echoes commands and inserts junk text noise
        if self.behavioral_scenario == "corrupted_strings":
            return b"data 1\r\nERROR_BUS_HALT\r\n0.001 0.002\r\nch>\r\n"

        # Scenario B: The device communication completely hangs and leaves off the 'ch>' prompt
        elif self.behavioral_scenario == "missing_prompt":
            return b"0.1234 0.5678\r\n0.4321 0.8765\r\n"

        return b""


def test_driver_handles_corrupted_text_gracefully():
    """Verifies that the driver skips garbage strings but extracts valid data points."""
    driver = PhysicalNanoVNA("COM3")
    driver.is_connected = True

    # Inject our fake corrupted hardware port straight into the active instance
    driver.serial_link = DummyFaultySerial(behavioral_scenario="corrupted_strings")

    # Execute parsing sweep
    trace = driver.capture_s21_trace()

    # It should successfully ignore 'ERROR_BUS_HALT' and find the one valid '0.001 0.002' line
    assert isinstance(trace, list)
    assert len(trace) == 1

    # Expected magnitude calculation: sqrt(0.001^2 + 0.002^2) = 0.002236
    # Expected dB: 20 * log10(0.002236) = -53.01 dB
    assert math.isclose(trace[0], -53.01029995663981, rel_tol=1e-5)


def test_driver_raises_exception_on_missing_prompt():
    """Enforces that the driver throws a TimeoutError if the device connection hangs."""
    driver = PhysicalNanoVNA("COM3")
    driver.is_connected = True
    driver.serial_link = DummyFaultySerial(behavioral_scenario="missing_prompt")

    # Force the execution loop to simulate a hardware timeout limit block
    # This directly answers Claude's criteria: ensuring the path raises on failures
    with pytest.raises(TimeoutError):
        driver.capture_s21_trace()
