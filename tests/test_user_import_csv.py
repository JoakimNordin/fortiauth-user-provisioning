"""Tests for fauth user-import-csv command."""
from __future__ import annotations

import pytest
import responses
from click.testing import CliRunner

from fauth.cli import main


BASE = "https://fac.example.com/api/v1"


@pytest.fixture
def runner():
    return CliRunner()


def _csv_file(tmp_path, content):
    p = tmp_path / "users.csv"
    p.write_text(content, encoding="utf-8")
    return p


@responses.activate
def test_import_csv_posts_content(runner, config_file, mock_keyring, audit_dir, tmp_path):
    csv = _csv_file(
        tmp_path,
        "username,first_name,last_name,email\n"
        "u1,John,Doe,j@x.se\n"
        "u2,Jane,Roe,jr@x.se\n",
    )
    responses.add(
        responses.POST,
        f"{BASE}/csv/localusers/",
        json={"imported": 2},
        status=200,
    )

    result = runner.invoke(main, ["user-import-csv", str(csv)])
    assert result.exit_code == 0, result.output
    assert "Imported 2 rows" in result.output


@responses.activate
def test_import_csv_dry_run_does_not_post(runner, config_file, mock_keyring, audit_dir, tmp_path):
    csv = _csv_file(
        tmp_path,
        "username,first_name,last_name,email\n"
        "u1,John,Doe,j@x.se\n",
    )

    result = runner.invoke(main, ["--dry-run", "user-import-csv", str(csv)])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    post_calls = [c for c in responses.calls if c.request.method == "POST"]
    assert post_calls == []


def test_import_csv_rejects_empty_file(runner, config_file, mock_keyring, audit_dir, tmp_path):
    csv = _csv_file(tmp_path, "")
    result = runner.invoke(main, ["user-import-csv", str(csv)])
    assert result.exit_code != 0
    assert "empty" in result.output.lower()


def test_import_csv_rejects_header_only(runner, config_file, mock_keyring, audit_dir, tmp_path):
    csv = _csv_file(tmp_path, "username,first_name,last_name,email\n")
    result = runner.invoke(main, ["user-import-csv", str(csv)])
    assert result.exit_code != 0
    assert "no data rows" in result.output.lower()
