from __future__ import annotations

import click


@click.command("user-addgroup")
@click.argument("username")
@click.argument("group")
@click.pass_obj
def cmd(ctx, username: str, group: str) -> None:
    """Add user to a group."""
    raise NotImplementedError(
        "user-addgroup: resolve user + group URIs, POST /localgroup-memberships/"
    )
