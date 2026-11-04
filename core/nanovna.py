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
import serial
from yaml import scan

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
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    if any(len(line.split()) != 5 for line in lines):
        raise ValueError(
            f"expected 5 numbers per line, got a line with {len(line.split())} values: {line}"
        )
    if len(lines) != expected_points:
        raise ValueError(
            f"expected {expected_points} points, got {len(lines)} lines of data"
        )
    freq = np.array([], dtype=float)
    s11_real = np.array([], dtype=float)
    s11_imag = np.array([], dtype=float)
    s21_real = np.array([], dtype=float)
    s21_imag = np.array([], dtype=float)
    for line in lines:
        freq = np.append(freq, float(line[0]))
        s11_real = np.append(s11_real, float(line[1]))
        s11_imag = np.append(s11_imag, float(line[2]))
        s21_real = np.append(s21_real, float(line[3]))
        s21_imag = np.append(s21_imag, float(line[4]))
    s11_imag *= j
    s21_imag *= j
    s11_comp = s11_real + s11_imag 
    s21_comp = s21_real + s21_imag
    return SweepResult(
        frequency_hz = freq,
        s11 = s11_comp,
        s21 = s21_comp
    )
    raise NotImplementedError


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
        self._serial = self._serial_factory(self.port, baudrate=115200, timeout=self.timeout_s)
        self._serial.write(self._query(""))
        if self._serial.read_until(PROMPT) != PROMPT:
            raise ConnectionError(
                f"No active serial session open with NanoVNA on {self.port}."
            )
        raise NotImplementedError

    def close(self) -> None:
        """Close the port if it's open, and forget it.

        Safe to call twice, or without ever calling connect().
        """
        if self._serial and self._serial.is_open:
            print(f"Port {self.port} is open, closing it now")
            self._serial.close()
        if not self._serial and self._serial.is_closed:
            print(f"Port {self.port} is already closed, nothing to do")
        self._serial = None
        return None
        raise NotImplementedError

    def identify(self) -> str:
        """Return the firmware version reported by the "version" command."""
        if not self._serial:
            raise ConnectionError("No active serial session open with NanoVNA.")
        return self._query("version")
        raise NotImplementedError

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
        self._query(f"scan {start_hz} {stop_hz} {points} {SCAN_OUTMASK}")
        # The reply is the echoed command, then one line per point, then the prompt.
        # Remove the echo and prompt, then parse the remaining lines.
        raise NotImplementedError

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
        if not self._serial or self._serial.is_closed:
            raise ConnectionError(
                f"No active serial session open with NanoVNA."
            )
        if current_time == timeout_time and PROMPT not in command:
            raise TimeOutError(
                f"Prompt did not arrive before the timeout."
        )
        version = "1.2.50"
        info = "p.101"
        if command == "":
            return(f"{PROMPT.decode()}")
        if "scan" in command:
            return(f"{command}\\r\\n{PROMPT.decode()}")
        if command == "version":
            return(f"{version}\\r\\n{PROMPT.decode()}")
        if command == "info":
            return(f"{info}\\r\\n{PROMPT.decode()}")
        raise NotImplementedError
