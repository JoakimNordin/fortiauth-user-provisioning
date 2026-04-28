from __future__ import annotations

import csv as csvlib
from pathlib import Path

import click

from fauth.audit import log_event
from fauth.client import FACError


@click.command("user-import-csv")
@click.argument("csv_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_obj
def cmd(ctx, csv_file: Path) -> None:
    """Bulk-import users from a CSV file via FAC's /csv/localusers/ endpoint.

    The CSV format is defined by FortiAuthenticator. Required columns
    typically include username, first_name, last_name, email. Group
    membership and FTM tokens are NOT handled by this endpoint - assign
    them afterwards with user-addgroup and user-enable-mfa.

    Use --dry-run to preview row count and field detection without uploading.
    """
    try:
        with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csvlib.reader(f)
            rows = list(reader)
    except (OSError, csvlib.Error) as e:
        click.echo(f"Error reading CSV: {e}", err=True)
        raise SystemExit(1)

    if not rows:
        click.echo("Error: CSV file is empty.", err=True)
        raise SystemExit(1)

    header = rows[0]
    data_rows = rows[1:]

    click.echo(f"File:        {csv_file}")
    click.echo(f"Header:      {', '.join(header)}")
    click.echo(f"Data rows:   {len(data_rows)}")

    if not data_rows:
        click.echo("Error: CSV has header only, no data rows.", err=True)
        raise SystemExit(1)

    if ctx.dry_run:
        click.echo("\n[dry-run] First 3 rows:")
        for row in data_rows[:3]:
            click.echo(f"  {row}")
        click.echo(f"\n[dry-run] POST /csv/localusers/ with {len(data_rows)} rows")
        return

    csv_text = csv_file.read_text(encoding="utf-8-sig")

    try:
        result = ctx.rw.post(
            "/csv/localusers/",
            json={"csv": csv_text},
        )
    except FACError as e:
        click.echo(f"Failed to import CSV: {e}", err=True)
        log_event(
            command="user-import-csv",
            instance=ctx.instance_name,
            result="failed",
            details={"file": str(csv_file), "rows": len(data_rows), "error": str(e)},
        )
        raise SystemExit(1)

    log_event(
        command="user-import-csv",
        instance=ctx.instance_name,
        result="success",
        details={"file": str(csv_file), "rows": len(data_rows)},
    )

    click.secho(
        f"\nImported {len(data_rows)} rows from {csv_file.name}.",
        fg="green",
    )
    if isinstance(result, dict):
        click.echo(f"FAC response: {result}")
