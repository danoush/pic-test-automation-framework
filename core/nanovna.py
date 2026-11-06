"""Driver for a NanoVNA-H over its USB serial shell.

Protocol facts, verified on our unit (NanoVNA-H, firmware 1.2.50, Nov 2026):
- Commands end with a carriage return ("\\r"). The shell prompt is "ch> ".
- The shell echoes each command back on its own line before the output.
- Output lines end with "\\r\\n".
- "scan START STOP POINTS 0b111" sweeps immediately and prints one line per
  point: "frequency_hz s11_real s11_imag s21_real s21_imag".
- "version" prints the firmware version, e.g. "1.2.50".
- At most 101 points per sweep ("info" reports "p:101").
- The port is native USB CDC (Windows shows "USB Serial Device"), so the baud
  rate setting is ignored. 115200 is just a conventional value.
"""

from cv2 import line
from matplotlib import text
from matplotlib import text
import serial
from yaml import scan
import numpy as np
import time
import io

from core.vna import VNA, SweepResult

PROMPT = b"ch> "
MAX_POINTS = 101
SCAN_OUTMASK = "0b111"  # bit 0: frequency, bit 1: S11, bit 2: S21


def parse_scan(text: str, expected_points: int) -> SweepResult:
    """Parse the output of "scan ... 0b111" into a SweepResult.

    Args:
        text: Scan output with the echo line and prompt already removed: one
            line per point, five whitespace-separated numbers each. Blank
            lines and trailing spaces are fine.
        expected_points: How many points the scan asked for.

    Returns:
        A SweepResult with float frequencies and complex S11/S21 arrays.

    Raises:
        ValueError: if any non-blank line isn't exactly five numbers, or the
            number of lines doesn't equal expected_points. Never skip a bad
            line: silently dropping a point corrupts the trace.
    """
    if not text.strip():
        raise ValueError("Scan output is empty.")
    
    try:
        data = np.loadtxt(io.StringIO(text), ndmin=2)
    except Exception as err:
        raise ValueError(f"Failed to parse scan text: {err}") from err

    if data.ndim != 2 or data.shape[1] != 5:
        raise ValueError("Each line must contain exactly 5 numbers.")
    
    if len(data) != expected_points:
        raise ValueError(f"expected {expected_points} points, got {len(data)} lines of data")

    freq = data[:, 0]
    s11_comp = data[:, 1] + 1j * data[:, 2]
    s21_comp = data[:, 3] + 1j * data[:, 4]

    return SweepResult(
        frequency_hz=freq, 
        s11=s11_comp, 
        s21=s21_comp
    )

class NanoVNA(VNA):
    """A NanoVNA-H connected over USB serial."""

    def __init__(self, port: str, timeout_s: float = 10.0, serial_factory=serial.Serial):
        """
        Args:
            port: Serial port name, e.g. "COM3".
            timeout_s: Longest wait, in seconds, for one command's reply.
            serial_factory: The function that opens the port. Normal code
                leaves the default; tests pass in a fake.
        """
        self.port = port
        self.timeout_s = timeout_s
        self._serial_factory = serial_factory
        self._serial = None  # the open port, set by connect()

    def connect(self) -> None:
        """Open the port and confirm that a NanoVNA shell answers.

        Open the port with
            self._serial_factory(self.port, baudrate=115200, timeout=self.timeout_s)
        then send an empty command (self._query("")) and wait for the prompt.

        Raises:
            ConnectionError: if the port can't be opened, or no prompt comes
                back. If the port opened but the prompt never came, close it
                before raising so it isn't left locked.
        """
        try:
            self._serial = self._serial_factory(self.port, baudrate=115200, timeout=self.timeout_s)
            self._query("")

        except serial.SerialException as err:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            raise ConnectionError(
                f"Failed to open serial port {self.port}: {err}"
            ) from err
        except TimeoutError as err:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            raise ConnectionError(
                f"No prompt received from NanoVNA on {self.port} within {self.timeout_s} seconds."
            ) from err
        except Exception as err:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            raise ConnectionError(
                f"Unexpected error while connecting to NanoVNA on {self.port}: {err}"
            ) from err

    def close(self) -> None:
        """Close the port if it's open, and forget it.

        Safe to call twice, or without ever calling connect().
        """
        if self._serial and self._serial.is_open:
            print(f"Port {self.port} is open, closing it now")
            self._serial.close()
        else:
            print(f"Port {self.port} is already closed, nothing to do")
        
        self._serial = None
        return None

    def identify(self) -> str:
        """Return the firmware version reported by the "version" command."""
        if not self._serial:
            raise ConnectionError("No active serial session open with NanoVNA.")
        return self._query("version")

    def measure(self, start_hz: float, stop_hz: float, points: int) -> SweepResult:
        """Sweep now with the "scan" command and return the parsed result.

        The command must use plain integers, e.g. "scan 50000 900000000 11 0b111",
        even when the caller passes floats like 50e3.

        Raises:
            ValueError: if start_hz <= 0, stop_hz <= start_hz, or points isn't
                between 2 and MAX_POINTS. Check before sending anything.
            ConnectionError: if called before connect().
        """
        start_hz = int(start_hz)
        stop_hz = int(stop_hz)
        if start_hz <= 0 or stop_hz <= start_hz or points < 2 or points > MAX_POINTS:
            raise ValueError(
                f"Error in starting/stopping frequency ({start_hz} Hz should be greater than 0 Hz and less than {stop_hz} Hz)"
                f"or number of points (should be greater than 1 and less than {MAX_POINTS})"
            )
        response_text = self._query(f"scan {start_hz} {stop_hz} {points} {SCAN_OUTMASK}")
        return parse_scan(response_text, expected_points=points)
        # The reply is the echoed command, then one line per point, then the prompt.
        # Remove the echo and prompt, then parse the remaining lines.

    def _query(self, command: str) -> str:
        """Send one shell command and return its output.

        Clear any stale input, send the command followed by "\\r", and read
        until the prompt arrives.

        Returns:
            The lines between the echoed command and the prompt, joined with
            "\\n" (no echo line, no prompt, no trailing newline). For
            "version" that's "1.2.50".

        Raises:
            ConnectionError: if not connected.
            TimeoutError: if the prompt doesn't arrive before the timeout.
        """
        if not self._serial or not self._serial.is_open:
            raise ConnectionError("No active serial session open with NanoVNA.")

        try:
            self._serial.reset_input_buffer()
            full_command = f"{command}\r".encode("ascii")
            self._serial.write(full_command)

            raw_response = self._serial.read_until(PROMPT)
            
            if not raw_response.endswith(PROMPT):
                raise TimeoutError(f"Prompt did not arrive before the timeout for command: {command!r}")

            response_str = raw_response.decode("ascii", errors="ignore")

            lines = response_str.splitlines()
            
            output_lines = []
            for line in lines:
                if line.strip() == PROMPT.decode().strip():
                    continue
                if command and line == command:
                    continue
                output_lines.append(line)

            return "\n".join(output_lines).strip()

        except serial.SerialException as err:
            raise ConnectionError(f"Serial communication error: {err}") from err
        except TimeoutError as err:
            raise err
        except Exception as err:
            raise ConnectionError(f"Unexpected error while querying NanoVNA: {err}") from err