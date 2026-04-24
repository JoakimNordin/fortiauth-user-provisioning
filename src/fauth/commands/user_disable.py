from __future__ import annotations

import click


@click.command("user-disable")
@click.argument("username")
@click.pass_obj
def cmd(ctx, username: str) -> None:
    """Disable a user (active=false). Does not remove group memberships."""
    raise NotImplementedError(
        "user-disable: GET user, PATCH /localusers/<id>/ {'active': false}"
    )
