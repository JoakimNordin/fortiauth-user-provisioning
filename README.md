# fauth

CLI for FortiAuthenticator 8.0.0 user provisioning via REST API. Automates
create/disable/delete of local users, group membership, and FTM token allocation.

Cross-platform: macOS, Windows, Linux. Ships as a single self-contained
binary (built with PyInstaller, no Python install needed on target machines).

## Install

```
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate.bat      # Windows cmd
# .venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -e .[dev]
```

## Configure

### Config file

Create `config.toml` at the OS-appropriate location:

| OS | Path |
|----|------|
| macOS / Linux | `~/.config/fauth/config.toml` |
| Windows | `%APPDATA%\fauth\config.toml` |

Override with the env var `FAUTH_CONFIG=/custom/path/config.toml` for testing.

Contents:

```toml
[fac.default]
host = "fac.example.com"             # your FortiAuthenticator hostname or IP
ro_keychain = "fauth-example-ro"     # keyring service name for the read-only key
rw_keychain = "fauth-example-rw"     # keyring service name for the read+write key

[defaults]
warn_tokens_below = 3
block_tokens_below = 1
license_prefix_allow = ["EFTM"]      # ignore FTMTRIAL* licenses for auto-allocation
```

### API keys - OS credential store

API keys are stored in the OS credential store via `keyring`:

| OS | Store |
|----|-------|
| macOS | Keychain (login.keychain) |
| Windows | Credential Manager |
| Linux | Secret Service / libsecret |

Cross-platform install via the `keyring` command (from the venv):

```
keyring set fauth-example-ro api_readonly       # paste the read-only API key
keyring set fauth-example-rw fauth-cli          # paste the read+write API key
```

The service names (`fauth-example-ro` / `fauth-example-rw`) must match
`ro_keychain` / `rw_keychain` in `config.toml`. The account names
(`api_readonly` / `fauth-cli`) should match the FortiAuthenticator admin
usernames you created for each API profile.

Or use OS-native tools:

- **macOS:** `security add-generic-password -U -s fauth-example-ro -a api_readonly -w`
- **Windows:** Credential Manager GUI → Add generic credential, Internet/Network Address = `fauth-example-ro`, User name = `api_readonly`, Password = the key

Verify with:

```
keyring get fauth-example-rw fauth-cli
```

### Audit log

Writes JSONL per write operation to:

| OS | Path |
|----|------|
| macOS / Linux | `~/.local/state/fauth/audit.log` |
| Windows | `%LOCALAPPDATA%\fauth\audit.log` |

## Usage

```
# Read commands
fauth groups                                  # list all groups
fauth groups --filter customer                # filter by prefix
fauth tokens                                  # FTM token pool status
fauth token-info <serial>                     # reverse-lookup which user holds a token

fauth user-show <username>                    # show a user
fauth user-list --group customer_admins       # list users in a group
fauth user-list --no-mfa                      # compliance check: users without MFA
fauth user-list --token-locked                # users assigned to a locked token
fauth user-search --email jdoe@acme.com       # find users by email/customer/ticket/name

# Lifecycle
fauth user-add --username jdoe \
    --first-name John --last-name Doe \
    --email jdoe@customer.com --mobile +46-701234567 \
    --group customer_admins --customer acme --ticket T-1234

fauth user-add --no-mfa --username svc-foo ...    # service account without token
fauth user-import-csv users.csv                   # bulk import via FAC's CSV endpoint

fauth user-update jdoe --email new@customer.com   # change attributes in-place
fauth user-disable jdoe
fauth user-enable jdoe                            # re-enable disabled user

# MFA management
fauth user-retoken jdoe                       # assign a new FTM token (phone change)
fauth user-enable-mfa jdoe                    # enable FTM on existing user without MFA
fauth user-disable-mfa jdoe                   # remove MFA, free token back to pool

# Group lifecycle
fauth group-create newcust_users              # create new group
fauth group-delete newcust_users              # delete (only if empty)
fauth user-addgroup jdoe customer_admins
fauth user-rmgroup jdoe customer_admins

# Hard delete
fauth user-delete jdoe
```

Use `--dry-run` on any write command to preview the request without calling FAC.

## Shell completion

### zsh (macOS/Linux)

```
mkdir -p ~/.config/fauth
_FAUTH_COMPLETE=zsh_source fauth > ~/.config/fauth/fauth-complete.zsh
echo 'source ~/.config/fauth/fauth-complete.zsh' >> ~/.zshrc
```

### bash

```
_FAUTH_COMPLETE=bash_source fauth > ~/.config/fauth/fauth-complete.bash
echo 'source ~/.config/fauth/fauth-complete.bash' >> ~/.bashrc
```

### PowerShell

```
_FAUTH_COMPLETE=powershell_source fauth > $env:APPDATA\fauth\fauth-complete.ps1
# add to $PROFILE:
. $env:APPDATA\fauth\fauth-complete.ps1
```

## Design notes

See [docs/DESIGN.md](docs/DESIGN.md) for known FortiAuthenticator 8.0.0 API
quirks (list vs dict responses, locked tokens, FTM activation mail race) and
the rationale behind the CLI surface.

## License

MIT (see [LICENSE](LICENSE)).
