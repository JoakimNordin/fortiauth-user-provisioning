# fauth

CLI for FortiAuthenticator 8.0.0 user provisioning.

Used internally at organization to automate user-add/remove flows against
customer FortiAuthenticator instances via the REST API.

## Install

```
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Configure

Create `~/.config/fauth/config.toml`:

```toml
[fac.default]
host = "fac.example.com"
ro_keychain = "fauth-example-ro"      # read-only Keychain service
rw_keychain = "fauth-example-rw"      # read+write Keychain service

[defaults]
warn_tokens_below = 3
block_tokens_below = 1
license_prefix_allow = ["EFTM"]
```

Store API keys in macOS Keychain (one-time):

```
security add-generic-password -U -s fauth-example-ro -a api_readonly -w
security add-generic-password -U -s fauth-example-rw -a fauth-cli -w
```

## Usage

```
fauth groups                                  # list all groups
fauth groups --filter customer                   # filter by prefix
fauth tokens                                  # FTM token pool status

fauth user-show <username>                    # show a user
fauth user-list --group fwint_admins          # list users in a group

fauth user-add --username jdoe \
    --first-name John --last-name Doe \
    --email jdoe@customer.com --mobile +46-701234567 \
    --group fwint_admins --customer example --ticket T-1234

fauth user-add --no-mfa --username svc-foo ...   # service account without token

fauth user-addgroup jdoe customer_customer
fauth user-rmgroup jdoe customer_customer
fauth user-disable jdoe
fauth user-delete jdoe
```

All write operations log JSONL to `~/.local/state/fauth/audit.log`.

## Project docs

See `CLAUDE.md` for links to the Obsidian project notes with full design rationale.
