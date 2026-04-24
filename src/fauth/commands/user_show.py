from __future__ import annotations

import click


@click.command("user-show")
@click.argument("username")
@click.pass_obj
def cmd(ctx, username: str) -> None:
    """Show a user by username."""
    raise NotImplementedError(
        "user-show: GET /localusers/?username__exact=X, format readable output"
    )
