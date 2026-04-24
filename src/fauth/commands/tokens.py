from __future__ import annotations

from collections import Counter, defaultdict

import click


@click.command("tokens")
@click.pass_obj
def cmd(ctx) -> None:
    """Show FortiToken pool status (assigned/available per license)."""
    tokens = ctx.ro.get_all("/fortitokens/", params={"limit": 100})

    # Count per-license: total, assigned, pending, locked (unallocatable), and
    # allocatable (status=available and not locked).
    by_license: dict[str, Counter[str]] = defaultdict(Counter)
    for t in tokens:
        lic = t.get("license") or "(unknown)"
        status = t.get("status") or "(unknown)"
        by_license[lic][status] += 1
        if status == "available":
            key = "allocatable" if not t.get("locked") else "locked"
            by_license[lic][key] += 1

    if not by_license:
        click.echo("No tokens found.")
        return

    lic_w = max(len(lic) for lic in by_license)
    lic_w = max(lic_w, len("License"))

    header = f"{'License':<{lic_w}}  {'Total':>5}  {'Assigned':>8}  {'Alloc.':>6}  {'Locked':>6}  {'Pending':>7}"
    click.echo(header)
    click.echo("-" * len(header))

    total_allocatable = 0
    total_allowed_allocatable = 0
    allowed = ctx.config.defaults.license_prefix_allow

    for lic in sorted(by_license):
        counts = by_license[lic]
        total = counts.get("available", 0) + counts.get("assigned", 0) + counts.get("pending", 0)
        allocatable = counts.get("allocatable", 0)
        allowed_match = any(lic.startswith(p) for p in allowed)
        marker = "" if allowed_match else "  (excluded - trial)"
        click.echo(
            f"{lic:<{lic_w}}  {total:>5}  {counts.get('assigned', 0):>8}  "
            f"{allocatable:>6}  {counts.get('locked', 0):>6}  "
            f"{counts.get('pending', 0):>7}{marker}"
        )
        total_allocatable += allocatable
        if allowed_match:
            total_allowed_allocatable += allocatable

    click.echo()
    click.echo(
        f"Total: {len(tokens)} tokens, "
        f"{total_allocatable} allocatable ({total_allowed_allocatable} from allowed licenses)"
    )

    warn = ctx.config.defaults.warn_tokens_below
    block = ctx.config.defaults.block_tokens_below
    if total_allowed_allocatable <= block:
        click.secho(
            f"CRITICAL: {total_allowed_allocatable} allocatable tokens from allowed licenses - user-add will be blocked.",
            fg="red",
            err=True,
        )
    elif total_allowed_allocatable < warn:
        click.secho(
            f"WARNING: only {total_allowed_allocatable} allocatable tokens (threshold {warn}). Order more licenses soon.",
            fg="yellow",
            err=True,
        )
