from __future__ import annotations

import os
import platform
import tomllib
from dataclasses import dataclass
from pathlib import Path

import keyring
from platformdirs import user_config_dir, user_state_dir


APP_NAME = "fauth"


def config_path() -> Path:
    """Resolve the config file path, prioritising explicit override and XDG on *nix."""
    # 1. Explicit override (testing, non-default locations)
    env_override = os.environ.get("FAUTH_CONFIG")
    if env_override:
        return Path(env_override)

    # 2. XDG-style on macOS/Linux (backwards compatible with pre-cross-platform layout)
    if platform.system() != "Windows":
        xdg_path = Path.home() / ".config" / APP_NAME / "config.toml"
        if xdg_path.exists():
            return xdg_path

    # 3. Platform default
    return Path(user_config_dir(APP_NAME, appauthor=False, roaming=False)) / "config.toml"


def state_dir() -> Path:
    """Directory for audit log and other state, XDG-style on *nix."""
    if platform.system() != "Windows":
        xdg = Path.home() / ".local" / "state" / APP_NAME
        if xdg.exists() or not _platformdirs_state_exists():
            return xdg
    return Path(user_state_dir(APP_NAME, appauthor=False, roaming=False))


def _platformdirs_state_exists() -> bool:
    return Path(user_state_dir(APP_NAME, appauthor=False, roaming=False)).exists()


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


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
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
    """Fetch a secret from the OS credential store via `keyring`.

    Works on macOS (Keychain), Windows (Credential Manager) and Linux (Secret
    Service / libsecret). Entries can be created with either the OS tool or
    `keyring set <service> <account>` from the terminal.
    """
    try:
        pw = keyring.get_password(service, account)
    except keyring.errors.KeyringError as e:
        raise RuntimeError(
            f"Keyring lookup failed for service={service} account={account}: {e}"
        ) from e
    if pw is None:
        raise RuntimeError(
            f"No keyring entry for service={service} account={account}. "
            f"Create it with: keyring set {service} {account}"
        )
    return pw
