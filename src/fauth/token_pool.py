"""Helpers for selecting FortiToken Mobile serials from the available pool."""
from __future__ import annotations

import click


def select_available_token(ctx, exclude_serials: set[str] | None = None) -> str | None:
    """Pick one FTM token serial from the allowed-license pool.

    Applies the standard filters:
      - status == "available"
      - type == "ftm"
      - locked == false (FAC rejects locked tokens on assignment)
      - license prefix in config.defaults.license_prefix_allow
      - optional: not in `exclude_serials` (e.g. current user's old token)

    Warns if allocatable count is below warn_tokens_below, blocks at
    block_tokens_below.

    Returns the serial (string) to assign, or None if blocked.
    """
    exclude_serials = exclude_serials or set()

    all_tokens = ctx.ro.get_all("/fortitokens/", params={"limit": 100})
    allowed = ctx.config.defaults.license_prefix_allow

    available = [
        t
        for t in all_tokens
        if t.get("status") == "available"
        and t.get("type") == "ftm"
        and not t.get("locked")
        and t.get("license")
        and any(t["license"].startswith(p) for p in allowed)
        and t.get("serial") not in exclude_serials
    ]

    count = len(available)
    warn = ctx.config.defaults.warn_tokens_below
    block = ctx.config.defaults.block_tokens_below

    if count <= block:
        click.secho(
            f"BLOCKED: only {count} tokens available from allowed licenses "
            f"(threshold {block}). Order more licenses before continuing.",
            fg="red",
            err=True,
        )
        return None

    if count < warn:
        click.secho(
            f"WARNING: only {count} tokens available (threshold {warn}). "
            f"Proceeding, but order more licenses soon.",
            fg="yellow",
            err=True,
        )

    chosen = available[0]
    serial = chosen.get("serial")
    if not serial:
        click.echo(f"Error: selected token has no serial number: {chosen}", err=True)
        return None
    return serial
