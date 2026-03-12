"""
Simple Ethernet client for the GAMMA VACUUM / DIGITEL SPCe ion pump controller.

Typical use:
- Set up the controller Ethernet settings from the front panel.
- Connect the controller to the computer by Ethernet.
- Use SPCeClient in a with-block or call connect() / close() manually.
- Device info is queried automatically on connect().
- Use the helper methods for common reads and settings.

This file also includes a small direct-run test at the bottom for quick debugging.
"""

import socket
import time
from enum import Enum
from types import TracebackType
from dataclasses import dataclass


class SPCeCommand(str, Enum):
    MODEL_NUMBER = "01"
    VERSION = "02"

    READ_CURRENT = "0A"
    READ_PRESSURE = "0B"
    READ_VOLTAGE = "0C"
    GET_SUPPLY_STATUS = "0D"

    SET_PRESSURE_UNITS = "0E"

    GET_PUMP_SIZE = "11"
    SET_PUMP_SIZE = "12"

    GET_CAL_FACTOR = "1D"
    SET_CAL_FACTOR = "1E"


class PressureUnit(str, Enum):
    TORR = "T"
    MBAR = "M"
    PASCAL = "P"


class ReadArgument(str, Enum):
    DEFAULT = ""
    CHANNEL_1 = "1"


class SPCeError(RuntimeError):
    """Raised when the controller returns a non-OK response."""

    def __init__(self, return_code: str, raw_reply: str) -> None:
        self.return_code: str = return_code
        self.raw_reply: str = raw_reply
        super().__init__(f"SPCe command failed with code {return_code}: {raw_reply}")

@dataclass(frozen=True)
class PressureReading:
    """Pressure value with unit."""
    value: float
    unit: str


class SPCeClient:
    """Small client for talking to the SPCe over Ethernet."""

    def __init__(
        self,
        IP: str,
        port: int = 23,
        connect_timeout: float = 5.0,
        read_timeout: float = 1.0,
    ) -> None:
        """Store connection settings."""
        self._IP: str = IP
        self._port: int = port
        self._connect_timeout: float = connect_timeout
        self._read_timeout: float = read_timeout

        self._sock: socket.socket | None = None
        self._model: str | None = None
        self._version: str | None = None

        # read-only properties
        @property
        def IP(self) -> str: """Device IP address."""; return self._IP
        @property
        def port(self) -> int: """TCP port number."""; return self._port
        @property
        def connect_timeout(self) -> float: """Socket connect timeout in seconds."""; return self._connect_timeout
        @property
        def read_timeout(self) -> float: """Socket read timeout in seconds."""; return self._read_timeout
        @property
        def model(self) -> str | None: """Detected device model."""; return self._model
        @property
        def version(self) -> str | None: """Detected firmware version."""; return self._version
        

    def __enter__(self) -> "SPCeClient":
        """Connect and return the client."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the connection on exit."""
        self.close()

    def __str__(self) -> str:
        """Return a short summary of the client and connected device."""
        if self._model is None and self._version is None:
            return (
                f"SPCeClient(IP={self._IP}, port={self._port}, "
                f"connected={self._sock is not None})"
            )

        return (
            f"SPCeClient(model={self._model}, version={self._version}, "
            f"IP={self._IP}, port={self._port}, connected={self._sock is not None})"
        )

    def connect(self) -> None:
        """Open the connection and read device info."""
        if self._sock is not None:
            return

        self._sock = socket.create_connection(
            (self._IP, self._port),
            timeout=self._connect_timeout,
        )
        self._sock.settimeout(self.read_timeout)

        try:
            self._model = self.get_model()
            self._version = self.get_version()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Close the connection and clear cached info."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None

        self._model = None
        self._version = None

    def send_raw(self, text: str, wait_time: float = 0.5) -> str:
        """Send one raw line and return the raw reply."""
        if self._sock is None:
            raise RuntimeError("Not connected. Call connect() first.")

        self._sock.sendall((text + "\r\n").encode("ascii"))
        time.sleep(wait_time)
        return self._sock.recv(4096).decode("ascii", errors="replace").strip()

    def send_command(
        self,
        command: SPCeCommand,
        *args: str,
        wait_time: float = 0.5,
    ) -> str:
        """Build and send one SPCe command."""
        parts: list[str] = ["spc", command.value]

        for arg in args:
            if arg != "":
                parts.append(arg)

        return self.send_raw(" ".join(parts), wait_time=wait_time)

    def query_payload(
        self,
        command: SPCeCommand,
        *args: str,
        wait_time: float = 0.5,
    ) -> str:
        """Send a command and return the payload."""
        raw_reply: str = self.send_command(command, *args, wait_time=wait_time)
        return self._parse_reply(raw_reply)

    def _parse_reply(self, raw_reply: str) -> str:
        """Check reply status and return the payload."""
        cleaned_lines: list[str] = []

        for line in raw_reply.splitlines():
            stripped_line: str = line.strip()
            stripped_line = stripped_line.lstrip(">").strip()
            if stripped_line:
                cleaned_lines.append(stripped_line)

        if not cleaned_lines:
            raise SPCeError("NO_REPLY", raw_reply)

        first_line: str = cleaned_lines[0]
        parts: list[str] = first_line.split(maxsplit=2)

        if len(parts) < 2:
            raise SPCeError("BAD_REPLY", raw_reply)

        status: str = parts[0]
        return_code: str = parts[1]
        payload: str = parts[2] if len(parts) >= 3 else ""

        if status != "OK":
            raise SPCeError(return_code, raw_reply)

        return payload.strip()

    def _parse_numeric_payload(self, payload: str) -> float:
        """Parse the first token of a numeric payload."""
        value_token: str = payload.split()[0]
        return float(value_token)

    def _parse_value_and_unit(self, payload: str) -> tuple[float, str]:
        """Parse a payload like '5.5E-07 Torr'."""
        parts: list[str] = payload.split()

        if len(parts) < 2:
            raise SPCeError("BAD_PAYLOAD", payload)

        value: float = float(parts[0])
        unit: str = parts[1]
        return value, unit

    def get_model(self) -> str:
        """Read the controller model."""
        return self.query_payload(SPCeCommand.MODEL_NUMBER)

    def get_version(self) -> str:
        """Read the firmware version."""
        payload: str = self.query_payload(SPCeCommand.VERSION)
        parts: list[str] = payload.split()

        if len(parts) >= 2 and parts[0].upper() == "FIRMWARE":
            return parts[1]

        return payload

    def get_supply_status(self) -> str:
        """Read the supply status."""
        return self.query_payload(SPCeCommand.GET_SUPPLY_STATUS)

    def get_current_A(self, arg: ReadArgument = ReadArgument.DEFAULT) -> float:
        """Read current in amps."""
        payload: str = self.query_payload(SPCeCommand.READ_CURRENT, arg.value)
        return self._parse_numeric_payload(payload)

    def get_pressure(self, arg: ReadArgument = ReadArgument.DEFAULT) -> PressureReading:
        """Read pressure with unit."""
        payload: str = self.query_payload(SPCeCommand.READ_PRESSURE, arg.value)
        value: float
        unit: str
        value, unit = self._parse_value_and_unit(payload)
        return PressureReading(value=value, unit=unit)

    def get_voltage_V(self, arg: ReadArgument = ReadArgument.DEFAULT) -> float:
        """Read voltage in volts."""
        payload: str = self.query_payload(SPCeCommand.READ_VOLTAGE, arg.value)
        return self._parse_numeric_payload(payload)

    def set_pressure_unit(self, unit: PressureUnit) -> None:
        """Set the pressure unit."""
        self.query_payload(SPCeCommand.SET_PRESSURE_UNITS, unit.value)

    def get_pump_size_Ls(self) -> float:
        """Read pump size in L/s."""
        payload: str = self.query_payload(SPCeCommand.GET_PUMP_SIZE)
        return self._parse_numeric_payload(payload)

    def set_pump_size_Ls(self, pump_size_Ls: int) -> None:
        """Set pump size in L/s."""
        self.query_payload(SPCeCommand.SET_PUMP_SIZE, f"{pump_size_Ls:04d}")

    def get_cal_factor(self) -> float:
        """Read the calibration factor."""
        payload: str = self.query_payload(SPCeCommand.GET_CAL_FACTOR)
        return self._parse_numeric_payload(payload)

    def set_cal_factor(self, cal_factor: float) -> None:
        """Set the calibration factor."""
        self.query_payload(SPCeCommand.SET_CAL_FACTOR, f"{cal_factor:.2f}")


if __name__ == "__main__":
    """Run a simple connection test from the terminal."""
    import argparse

    def parse_args() -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            description="Simple Ethernet client for the GAMMA VACUUM / DIGITEL SPCe ion pump controller."
        )
        parser.add_argument(
            "--IP",
            type=str,
            default="192.168.1.50",
            help="SPCe IP address. Defaults to 192.168.1.50.",
        )
        return parser.parse_args()

    args: argparse.Namespace = parse_args()
    IP: str = input(f"SPCe IP address [if blank, {args.IP}]: ").strip() or args.IP
    print()

    with SPCeClient(IP) as client:
        print(client)
        print()

        pressure: PressureReading = client.get_pressure()
        print("Pressure:", pressure.value, pressure.unit)
        current_A: float = client.get_current_A()
        print("Current [A]:", current_A)
        voltage_V: float = client.get_voltage_V()
        print("Voltage [V]:", voltage_V)
        
        
        