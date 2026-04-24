from __future__ import annotations

import click


@click.command("user-list")
@click.option("--group", help="Filter by group name")
@click.option("--customer", help="Filter by custom1 (kundkod)")
@click.pass_obj
def cmd(ctx, group: str | None, customer: str | None) -> None:
    """List users, optionally filtered by group or customer."""
    raise NotImplementedError(
        "user-list: GET /localusers/ or via /localgroup-memberships/ if --group"
    )
