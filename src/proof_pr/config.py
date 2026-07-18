from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a repository configuration is invalid."""


@dataclass(frozen=True)
class VerificationConfig:
    base: str | None = None
    checks: tuple[tuple[str, tuple[str, ...]], ...] = ()
    timeout_seconds: int | None = None
    output_dir: Path | None = None


def _unknown_keys(value: dict[str, Any], allowed: set[str], *, location: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        rendered = ", ".join(unknown)
        raise ConfigError(f"unknown {location} key(s): {rendered}")


def _optional_string(value: Any, *, location: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{location} must be a non-empty string")
    return value.strip()


def load_config(path: Path) -> VerificationConfig:
    """Load repository-owned verification defaults from TOML."""

    if not path.exists():
        return VerificationConfig()

    try:
        with path.open("rb") as config_file:
            payload = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    _unknown_keys(payload, {"verify"}, location="top-level")
    verify = payload.get("verify", {})
    if not isinstance(verify, dict):
        raise ConfigError("verify must be a table")
    _unknown_keys(
        verify,
        {"base", "checks", "timeout", "output_dir"},
        location="verify",
    )

    base = _optional_string(verify.get("base"), location="verify.base")

    timeout = verify.get("timeout")
    if timeout is not None and (
        not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0
    ):
        raise ConfigError("verify.timeout must be a positive integer")

    raw_output_dir = _optional_string(
        verify.get("output_dir"),
        location="verify.output_dir",
    )
    output_dir = Path(raw_output_dir) if raw_output_dir is not None else None

    raw_checks = verify.get("checks", [])
    if not isinstance(raw_checks, list):
        raise ConfigError("verify.checks must be an array of tables")

    checks: list[tuple[str, tuple[str, ...]]] = []
    names: set[str] = set()
    for index, raw_check in enumerate(raw_checks):
        location = f"verify.checks[{index}]"
        if not isinstance(raw_check, dict):
            raise ConfigError(f"{location} must be a table")
        _unknown_keys(raw_check, {"name", "command"}, location=location)

        name = _optional_string(raw_check.get("name"), location=f"{location}.name")
        if name is None:
            raise ConfigError(f"{location}.name is required")
        if name in names:
            raise ConfigError(f"duplicate check name: {name}")

        command = raw_check.get("command")
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) and part for part in command)
        ):
            raise ConfigError(f"{location}.command must be a non-empty array of strings")

        names.add(name)
        checks.append((name, tuple(command)))

    return VerificationConfig(
        base=base,
        checks=tuple(checks),
        timeout_seconds=timeout,
        output_dir=output_dir,
    )
