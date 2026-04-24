from __future__ import annotations

import click


@click.command("groups")
@click.option("--filter", "filter_prefix", help="Only show groups whose name starts with this prefix")
@click.pass_obj
def cmd(ctx, filter_prefix: str | None) -> None:
    """List user groups with member counts and URIs."""
    raise NotImplementedError("groups: GET /usergroups/, render table")
