from __future__ import annotations

import click


@click.command("user-add")
@click.option("--username", required=True, help="Username requested by customer")
@click.option("--first-name", required=True)
@click.option("--last-name", required=True)
@click.option("--email", required=True, help="Used for password + FTM activation mail")
@click.option("--mobile", help="Format: +46-701234567 (optional for email-activated FTM)")
@click.option("--group", "groups", multiple=True, required=True, help="Group name (can repeat)")
@click.option("--customer", help="Customer code, stored in custom1")
@click.option("--ticket", help="Ticket ID, stored in custom2")
@click.option("--no-mfa", is_flag=True, help="Create as service account without FTM token")
@click.option(
    "--sms-activation",
    is_flag=True,
    help="Use SMS instead of email for FTM activation (requires --mobile)",
)
@click.pass_obj
def cmd(
    ctx,
    username: str,
    first_name: str,
    last_name: str,
    email: str,
    mobile: str | None,
    groups: tuple[str, ...],
    customer: str | None,
    ticket: str | None,
    no_mfa: bool,
    sms_activation: bool,
) -> None:
    """Create a user with MFA (default) and group membership(s).

    Flow:
      1. If MFA on: GET /fortitokens/?status=available, filter allowed licenses,
         warn if below threshold, block if at zero.
      2. POST /localusers/ with payload.
      3. For each group: GET /usergroups/?name__exact=X, POST /localgroup-memberships/.
      4. On any failure after POST /localusers/: rollback via DELETE.
      5. Audit log + print summary (FAC sends activation mail automatically).
    """
    raise NotImplementedError("user-add: see docstring for flow")
