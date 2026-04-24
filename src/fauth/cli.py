from __future__ import annotations

import sys

import click

from fauth import __version__
from fauth.client import FACClient, FACError
from fauth.config import Config, load_config, keychain_password


class Context:
    def __init__(self, config: Config, instance_name: str, dry_run: bool, verbose: bool):
        self.config = config
        self.instance_name = instance_name
        self.instance = config.instances[instance_name]
        self.dry_run = dry_run
        self.verbose = verbose
        self._ro: FACClient | None = None
        self._rw: FACClient | None = None

    @property
    def ro(self) -> FACClient:
        if self._ro is None:
            key = keychain_password(self.instance.ro_keychain, _account_for(self.instance.ro_keychain))
            self._ro = FACClient(self.instance.host, _account_for(self.instance.ro_keychain), key)
        return self._ro

    @property
    def rw(self) -> FACClient:
        if self._rw is None:
            account = _account_for(self.instance.rw_keychain)
            key = keychain_password(self.instance.rw_keychain, account)
            self._rw = FACClient(self.instance.host, account, key)
        return self._rw


def _account_for(keychain_service: str) -> str:
    """Map Keychain service name to account name.

    Convention: fauth-<instance>-ro → api_readonly, fauth-<instance>-rw → fauth-cli.
    Override by adjusting config if convention differs.
    """
    if keychain_service.endswith("-ro"):
        return "api_readonly"
    if keychain_service.endswith("-rw"):
        return "fauth-cli"
    raise ValueError(f"Cannot derive account from keychain service {keychain_service}")


@click.group()
@click.version_option(__version__)
@click.option("--instance", default="default", show_default=True, help="FAC instance from config.toml")
@click.option("--dry-run", is_flag=True, help="Show what would happen, do not call write endpoints")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output (log HTTP details)")
@click.pass_context
def main(ctx: click.Context, instance: str, dry_run: bool, verbose: bool) -> None:
    """FortiAuthenticator user provisioning CLI."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    if instance not in config.instances:
        click.echo(f"Error: unknown instance '{instance}'. Known: {list(config.instances)}", err=True)
        sys.exit(2)

    ctx.obj = Context(config=config, instance_name=instance, dry_run=dry_run, verbose=verbose)


# Import and register subcommands
from fauth.commands import (
    groups,
    tokens,
    user_show,
    user_list,
    user_add,
    user_disable,
    user_delete,
    user_addgroup,
    user_rmgroup,
)

main.add_command(groups.cmd)
main.add_command(tokens.cmd)
main.add_command(user_show.cmd)
main.add_command(user_list.cmd)
main.add_command(user_add.cmd)
main.add_command(user_disable.cmd)
main.add_command(user_delete.cmd)
main.add_command(user_addgroup.cmd)
main.add_command(user_rmgroup.cmd)


def run() -> None:
    try:
        main(standalone_mode=False)
    except FACError as e:
        click.echo(f"FAC error: {e}", err=True)
        sys.exit(1)
    except click.ClickException:
        raise
    except Exception as e:  # noqa: BLE001
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
