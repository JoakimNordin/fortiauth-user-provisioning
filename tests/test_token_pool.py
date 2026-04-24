"""Tests for token_pool.select_available_token filtering and thresholds."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fauth.config import Defaults
from fauth.token_pool import select_available_token


class FakeCtx:
    """Minimal ctx that select_available_token needs."""

    def __init__(self, tokens, license_allow=("EFTM",), warn=0, block=0):
        self.ro = MagicMock()
        self.ro.get_all.return_value = tokens
        self.config = MagicMock()
        self.config.defaults = Defaults(
            warn_tokens_below=warn,
            block_tokens_below=block,
            license_prefix_allow=license_allow,
        )


def token(serial="FTKMOB-1", status="available", type_="ftm", locked=False, license_="EFTM-PROD"):
    return {
        "serial": serial,
        "status": status,
        "type": type_,
        "locked": locked,
        "license": license_,
    }


def test_picks_first_available_token():
    ctx = FakeCtx([token(serial="A"), token(serial="B"), token(serial="C")])
    assert select_available_token(ctx) == "A"


def test_skips_locked_tokens():
    ctx = FakeCtx([
        token(serial="LOCKED", locked=True),
        token(serial="UNLOCKED", locked=False),
    ])
    assert select_available_token(ctx) == "UNLOCKED"


def test_skips_assigned_tokens():
    ctx = FakeCtx([
        token(serial="TAKEN", status="assigned"),
        token(serial="FREE", status="available"),
    ])
    assert select_available_token(ctx) == "FREE"


def test_skips_non_ftm_types():
    ctx = FakeCtx([
        token(serial="HW", type_="ftk"),
        token(serial="MOB", type_="ftm"),
    ])
    assert select_available_token(ctx) == "MOB"


def test_skips_trial_license_prefix():
    ctx = FakeCtx([
        token(serial="TRIAL", license_="FTMTRIAL-123"),
        token(serial="PROD", license_="EFTM-PROD"),
    ])
    assert select_available_token(ctx) == "PROD"


def test_skips_tokens_with_null_license():
    ctx = FakeCtx([
        token(serial="NULL", license_=None),
        token(serial="OK", license_="EFTM-PROD"),
    ])
    assert select_available_token(ctx) == "OK"


def test_exclude_serials_skips_current_token():
    """Used by user-retoken to avoid re-assigning the same serial."""
    ctx = FakeCtx([
        token(serial="CURRENT"),
        token(serial="NEW"),
    ])
    result = select_available_token(ctx, exclude_serials={"CURRENT"})
    assert result == "NEW"


def test_blocks_when_pool_at_threshold(capsys):
    """When count <= block_tokens_below, return None + print critical."""
    ctx = FakeCtx([token(serial="ONLY")], block=1, warn=3)
    result = select_available_token(ctx)
    assert result is None
    captured = capsys.readouterr()
    assert "BLOCKED" in captured.err


def test_warns_when_pool_near_empty(capsys):
    ctx = FakeCtx(
        [token(serial="A"), token(serial="B")],
        block=0, warn=3,
    )
    result = select_available_token(ctx)
    assert result == "A"
    captured = capsys.readouterr()
    assert "WARNING" in captured.err


def test_no_warning_when_pool_is_healthy(capsys):
    ctx = FakeCtx(
        [token(serial=f"T{i}") for i in range(10)],
        block=1, warn=3,
    )
    select_available_token(ctx)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err
    assert "BLOCKED" not in captured.err


def test_all_filters_combined():
    """Realistic mix: assigned, locked, trial - only one valid token."""
    ctx = FakeCtx([
        token(serial="A", status="assigned"),
        token(serial="B", locked=True),
        token(serial="C", license_="FTMTRIAL-X"),
        token(serial="D", type_="ftk"),
        token(serial="E"),
    ])
    assert select_available_token(ctx) == "E"
