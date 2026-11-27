"""Resolve serial settings from TOML and command-line overrides."""

import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from pathlib import Path


DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 2.0


class ConfigError(ValueError):
    """Serial settings could not be loaded or validated."""


@dataclass(frozen=True)
class SerialSettings:
    port: str
    baudrate: int = DEFAULT_BAUDRATE
    timeout: float = DEFAULT_TIMEOUT


def serial_settings(
    path: Path | None = None,
    *,
    port: str | None = None,
    baudrate: int | None = None,
    timeout: float | None = None,
    default_port: Callable[[], str] | None = None,
) -> SerialSettings:
    values = {}
    if path is not None:
        try:
            with path.open("rb") as config_file:
                values = tomllib.load(config_file).get("serial", {})
        except (OSError, ValueError) as error:
            raise ConfigError(f"Could not read config {str(path)!r}: {error}") from error
        if not isinstance(values, dict):
            raise ConfigError(f"The serial setting in {str(path)!r} must be a [serial] table.")
        unknown = values.keys() - {"port", "baudrate", "timeout"}
        if unknown:
            raise ConfigError(f"Unknown [serial] settings: {', '.join(sorted(unknown))}.")

    if port is None:
        port = values.get("port")
    if port is None and default_port is not None:
        port = default_port()
    if port is None:
        raise ConfigError("Choose a port from 'cardaq ports'. Set --port or [serial].port.")
    if not isinstance(port, str) or not port.strip():
        raise ConfigError("The serial port must be a nonempty device name.")

    if baudrate is None:
        baudrate = values.get("baudrate", DEFAULT_BAUDRATE)
    if type(baudrate) is not int or baudrate <= 0:
        raise ConfigError("The serial baud rate must be a positive integer.")

    if timeout is None:
        timeout = values.get("timeout", DEFAULT_TIMEOUT)
    try:
        timeout = float(timeout) if type(timeout) in (int, float) else 0.0
    except OverflowError as error:
        raise ConfigError("The serial timeout must be a finite positive number in seconds.") from error
    if not isfinite(timeout) or timeout <= 0:
        raise ConfigError("The serial timeout must be a finite positive number in seconds.")

    return SerialSettings(port, baudrate, timeout)
