from __future__ import annotations

import click


@click.command("user-delete")
@click.argument("username")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def cmd(ctx, username: str, yes: bool) -> None:
    """Delete a user. Memberships are removed by FAC cascading on user delete."""
    raise NotImplementedError(
        "user-delete: GET user, confirm unless --yes, DELETE /localusers/<id>/"
    )
