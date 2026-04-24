from __future__ import annotations

import click


@click.command("tokens")
@click.pass_obj
def cmd(ctx) -> None:
    """Show FortiToken pool status (assigned/available per license)."""
    raise NotImplementedError(
        "tokens: GET /fortitokens/, group by license + status, warn if below threshold"
    )
