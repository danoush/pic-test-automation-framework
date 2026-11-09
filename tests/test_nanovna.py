"""Tests for core/nanovna.py.

The fixture and the canned replies below are real output from our NanoVNA-H
(firmware 1.2.50), captured with nothing connected to either port.
Run with:  pytest tests/test_nanovna.py -x   (-x stops at the first failure)
"""

from pathlib import Path

import numpy as np
import pytest
import serial

from core.nanovna import NanoVNA, parse_scan, SyncError
from core.vna import SweepResult

FIXTURES = Path(__file__).parent / "fixtures"
SCAN_TEXT = (FIXTURES / "scan_11pt_ports_open.txt").read_text(encoding="utf-8")

WAKE = b"\r"                  # an empty command
WAKE_REPLY = b"\r\nch> "      # the shell just prints a fresh prompt
SCAN_COMMAND = b"scan 50000 900000000 11 0b111\r"
SCAN_REPLY = (
    b"scan 50000 900000000 11 0b111\r\n"                      # the echo
    + SCAN_TEXT.replace("\n", "\r\n").encode("ascii")         # the data lines
    + b"ch> "                                                 # the prompt
)


class FakeSerial:
    """Stands in for serial.Serial: replies to each known command with canned bytes."""

    def __init__(self, replies):
        self.replies = replies        # {bytes written: bytes the device sends back}
        self.written = []             # every write(), in order
        self.is_open = True
        self._unread = b""

    def write(self, data):
        if not self.is_open:
            raise serial.PortNotOpenError()  # what real pyserial does
        self.written.append(data)
        if data not in self.replies:
            raise AssertionError(
                f"driver wrote {data!r}, which this test doesn't expect. "
                f"Known commands: {list(self.replies)}"
            )
        self._unread += self.replies[data]
        return len(data)

    def read_until(self, expected=b"\n", size=None):
        # Like pyserial: return right after `expected`. If it never arrives, a
        # real port returns whatever it got once the timeout runs out; the fake
        # returns that immediately.
        end = self._unread.find(expected)
        end = len(self._unread) if end == -1 else end + len(expected)
        data, self._unread = self._unread[:end], self._unread[end:]
        return data

    def reset_input_buffer(self):
        self._unread = b""

    def reset_output_buffer(self):
        pass

    def flush(self):
        pass

    def close(self):
        self.is_open = False


def connected_vna(replies):
    """A NanoVNA wired to a FakeSerial, already connected."""
    fake = FakeSerial({WAKE: WAKE_REPLY, **replies})
    vna = NanoVNA("COM_TEST", serial_factory=lambda *args, **kwargs: fake)
    vna.connect()
    return vna, fake


# ---------- parse_scan: pure parsing, no serial port involved ----------

def test_parse_scan_reads_real_capture():
    result = parse_scan(SCAN_TEXT, expected_points=11)

    assert isinstance(result, SweepResult)
    assert len(result.frequency_hz) == 11
    assert result.frequency_hz[0] == 50_000
    assert result.frequency_hz[-1] == 900_000_000
    assert result.s11[0] == pytest.approx(complex(1.001013517, -0.001039236))
    assert result.s21[-1] == pytest.approx(complex(0.000328795, 0.000155340))


def test_parse_scan_matches_the_physics_of_open_ports():
    result = parse_scan(SCAN_TEXT, expected_points=11)

    assert np.iscomplexobj(result.s11) and np.iscomplexobj(result.s21)
    # An open port reflects almost everything, and nothing reaches port 2.
    assert np.all(np.abs(result.s11) > 0.95)
    assert np.all(np.abs(result.s21) < 0.01)


def test_parse_scan_rejects_wrong_point_count():
    with pytest.raises(ValueError):
        parse_scan(SCAN_TEXT, expected_points=101)


def test_parse_scan_rejects_garbage_line():
    # The old driver skipped lines like this. The garbage is inserted as an
    # extra line, so a parser that skips it would still count 11 good points
    # and wrongly pass.
    lines = SCAN_TEXT.splitlines()
    lines.insert(3, "ERROR_BUS_HALT")
    with pytest.raises(ValueError):
        parse_scan("\n".join(lines), expected_points=11)


def test_parse_scan_rejects_line_with_missing_value():
    lines = SCAN_TEXT.splitlines()
    lines.insert(5, "450025000 0.995685248 0.005025715 -0.000153075")  # S21 imag lost
    with pytest.raises(ValueError):
        parse_scan("\n".join(lines), expected_points=11)


def test_parse_scan_rejects_empty_output():
    with pytest.raises(ValueError):
        parse_scan("", expected_points=11)


# ---------- connect ----------

def test_connect_opens_port_with_a_timeout_and_wakes_the_shell():
    # Without a timeout, a missing prompt would hang the program forever.
    calls = []
    fake = FakeSerial({WAKE: WAKE_REPLY})

    def factory(*args, **kwargs):
        calls.append((args, kwargs))
        return fake

    vna = NanoVNA("COM_TEST", timeout_s=2.5, serial_factory=factory)
    vna.connect()

    args, kwargs = calls[0]
    assert (args[0] if args else kwargs.get("port")) == "COM_TEST"
    assert kwargs.get("timeout") == 2.5
    assert fake.written == [WAKE]


def test_connect_raises_connection_error_when_port_wont_open():
    def broken_factory(*args, **kwargs):
        raise serial.SerialException("could not open port 'COM_TEST'")

    vna = NanoVNA("COM_TEST", serial_factory=broken_factory)
    with pytest.raises(ConnectionError):
        vna.connect()


def test_connect_raises_and_closes_port_when_no_prompt_arrives():
    # Wrong device on the port: it answers, but never with "ch> ".
    fake = FakeSerial({WAKE: b"garbage"})
    vna = NanoVNA("COM_TEST", serial_factory=lambda *args, **kwargs: fake)
    with pytest.raises(ConnectionError):
        vna.connect()
    assert fake.is_open is False


# ---------- identify ----------

def test_identify_returns_firmware_version():
    vna, fake = connected_vna({b"version\r": b"version\r\n1.2.50\r\nch> "})
    assert vna.identify() == "1.2.50"
    assert fake.written[-1] == b"version\r"


def test_identify_raises_timeout_when_prompt_never_arrives():
    # The reply stops before "ch> ", like a device that hung mid-response.
    vna, fake = connected_vna({b"version\r": b"version\r\n1.2.50\r\n"})
    with pytest.raises(TimeoutError):
        vna.identify()


# ---------- measure ----------

def test_measure_sends_scan_and_returns_parsed_sweep():
    vna, fake = connected_vna({SCAN_COMMAND: SCAN_REPLY})

    # Engineers write 50e3 and 900e6; the command must still use plain integers.
    result = vna.measure(50e3, 900e6, 11)

    assert fake.written[-1] == SCAN_COMMAND
    assert len(result.frequency_hz) == 11
    assert result.s11[0] == pytest.approx(complex(1.001013517, -0.001039236))


@pytest.mark.parametrize(
    "start_hz, stop_hz, points",
    [
        (0, 900e6, 11),       # start must be above 0 Hz
        (900e6, 50e3, 11),    # stop must be above start
        (50e3, 900e6, 1),     # a sweep needs at least 2 points
        (50e3, 900e6, 102),   # this NanoVNA-H tops out at 101 points
    ],
)
def test_measure_rejects_bad_arguments_before_sending_anything(start_hz, stop_hz, points):
    vna, fake = connected_vna({})
    with pytest.raises(ValueError):
        vna.measure(start_hz, stop_hz, points)
    assert fake.written == [WAKE]  # nothing sent after the connect handshake


def test_measure_requires_connection():
    vna = NanoVNA("COM_TEST", serial_factory=lambda *args, **kwargs: FakeSerial({}))
    with pytest.raises(ConnectionError):
        vna.measure(50e3, 900e6, 11)


# ---------- close and the with-block ----------

def test_close_is_safe_before_connect_and_twice():
    NanoVNA("COM_TEST").close()  # never connected: nothing to do, no error

    vna, fake = connected_vna({})
    vna.close()
    vna.close()
    assert fake.is_open is False


def test_measure_after_close_raises_connection_error():
    vna, fake = connected_vna({SCAN_COMMAND: SCAN_REPLY})
    vna.close()
    with pytest.raises(ConnectionError):
        vna.measure(50e3, 900e6, 11)


def test_with_block_closes_port_even_after_an_error():
    fake = FakeSerial({WAKE: WAKE_REPLY})
    vna = NanoVNA("COM_TEST", serial_factory=lambda *args, **kwargs: fake)

    with pytest.raises(ValueError):
        with vna:
            vna.measure(900e6, 50e3, 11)  # bad arguments raise inside the block

    assert fake.is_open is False

# ---------- added after the M2 review ----------

def test_measure_rejects_corrupted_bytes():
    # One byte damaged on the wire: a "0" inside the first S11 value became 0xFF.
    # Silently dropping the bad byte would turn 1.001013517 into 1.01013517.
    corrupted = SCAN_REPLY.replace(b"1.001013517", b"1.0\xff1013517", 1)
    vna, fake = connected_vna({SCAN_COMMAND: corrupted})
    with pytest.raises(ValueError):  # UnicodeDecodeError is a kind of ValueError
        vna.measure(50e3, 900e6, 11)


def test_bugs_are_not_disguised_as_connection_errors():
    # A programming bug must surface as itself. Reported as a ConnectionError,
    # it would send you off checking cables instead of reading the traceback.
    vna, fake = connected_vna({b"version\r": b"version\r\n1.2.50\r\nch> "})

    def broken_read_until(*args, **kwargs):
        raise RuntimeError("stand-in for a bug in the read code")

    fake.read_until = broken_read_until
    with pytest.raises(RuntimeError):
        vna.identify()

# ---------- added after the M3 review ----------

def test_wrong_echo_raises_sync_error():
    vna, fake = connected_vna({b"version\r": b"garbage\r\nch> "})
    with pytest.raises(SyncError):
        vna.identify()
    assert fake.written[-1] == b"version\r"

def test_connect_closes_port_on_wrong_echo():
    fake = FakeSerial({WAKE: b"garbage\r\nch> "})
    vna = NanoVNA("COM_TEST", serial_factory=lambda *args, **kwargs: fake)
    with pytest.raises(ConnectionError):
        vna.connect()
    assert not fake.is_open
