from __future__ import annotations

import click


@click.command("user-rmgroup")
@click.argument("username")
@click.argument("group")
@click.pass_obj
def cmd(ctx, username: str, group: str) -> None:
    """Remove user from a group."""
    raise NotImplementedError(
        "user-rmgroup: find membership via GET /localgroup-memberships/?user=X&group=Y, DELETE"
    )
