from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "fauth" / "config.toml"


@dataclass(frozen=True)
class FacInstance:
    name: str
    host: str
    ro_keychain: str
    rw_keychain: str


@dataclass(frozen=True)
class Defaults:
    warn_tokens_below: int = 3
    block_tokens_below: int = 1
    license_prefix_allow: tuple[str, ...] = ("EFTM",)


@dataclass(frozen=True)
class Config:
    instances: dict[str, FacInstance]
    defaults: Defaults


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Create it per README.md."
        )
    with path.open("rb") as f:
        raw = tomllib.load(f)

    instances = {}
    for name, data in raw.get("fac", {}).items():
        instances[name] = FacInstance(
            name=name,
            host=data["host"],
            ro_keychain=data["ro_keychain"],
            rw_keychain=data["rw_keychain"],
        )

    d = raw.get("defaults", {})
    defaults = Defaults(
        warn_tokens_below=d.get("warn_tokens_below", 3),
        block_tokens_below=d.get("block_tokens_below", 1),
        license_prefix_allow=tuple(d.get("license_prefix_allow", ["EFTM"])),
    )

    return Config(instances=instances, defaults=defaults)


def keychain_password(service: str, account: str) -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Keychain lookup failed for service={service} account={account}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()
