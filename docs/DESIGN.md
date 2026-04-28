# Design notes

## Command surface

19 commands grouped by purpose. Read commands work with a FortiAuthenticator
admin profile limited to "Users and Devices" Read-Only; write commands
require Read+Write on the same scope.

**Read (read-only profile sufficient):**

- `groups` - list user groups with member counts
- `tokens` - FortiToken pool status per license, including allocatable count
- `token-info <serial>` - reverse-lookup which user holds a specific token
- `user-show <username>` - show a user record
- `user-list` - list users, with filters: `--group`, `--customer`, `--inactive`,
  `--no-mfa` (compliance), `--token-locked` (locked-pool diagnostics)
- `user-search` - find users by `--email`, `--customer`, `--ticket`, or
  `--name`. Useful when only a piece of metadata is known

**User lifecycle (write):**

- `user-add` - create user, auto-allocate FTM token, add to groups in one
  flow. `--no-mfa` for service accounts. `--dry-run` to preview
- `user-update` - patch attributes (first/last name, email, mobile, customer,
  ticket) without recreating the user
- `user-disable` / `user-enable` - toggle `active` flag
- `user-delete` - hard delete with confirmation prompt (`--yes` to skip)
- `user-import-csv` - bulk import via FAC's `/csv/localusers/` endpoint

**MFA management (write):**

- `user-enable-mfa` - enable FTM on an existing user that doesn't have MFA
  (e.g. created via GUI or `user-add --no-mfa`). Picks a token, PATCHes
  user, FAC mails activation
- `user-retoken` - swap FTM token on a user who already has MFA (phone
  change). Excludes the current serial from selection
- `user-disable-mfa` - remove MFA, frees the token back to the pool

**Group lifecycle (write):**

- `group-create` - create empty group with `--type` (firewall/vpn/radius/tacacs+)
- `group-delete` - delete group, refuses if non-empty (forces the operator
  to empty it first via `user-rmgroup`)
- `user-addgroup` / `user-rmgroup` - manage individual memberships

Why two separate admin profiles (+ two keyring entries)? Principle of least
privilege: most day-to-day operations are lookups, which never need write
access. Read-only credentials are also safer to share between automated
scripts that only produce reports.

## MFA flow

Default is FortiToken Mobile (FTM) with email activation. Observed in the
wild: roughly half of existing users use FTM, the rest are service accounts
without MFA. `user-add` picks an available token from the allowed license
pool, passes `token_serial` on the user payload, and lets FortiAuthenticator
mail the activation code to the user's email.

## Token pool management

`fauth tokens` distinguishes:

- **Available** - status reported by the API
- **Allocatable** - status=available AND locked=false (what `user-add` can
  actually use)

The distinction matters because FortiAuthenticator marks some "available"
tokens as `locked: true`, and assigning them returns `400 {"error": "This
serial number is not available for use."}`. The CLI filters them out
automatically and warns if the allocatable count drops below the configured
threshold.

## FortiAuthenticator 8.0.0 API quirks

Discovered during PoC and worked around in the code:

### 1. API keys are delivered by email, not shown in the GUI

Enabling Web Service Access on an admin user mails the API key to that
admin's email. There is no "copy key" button. If the key is lost, toggle Web
Service Access off/on to trigger a new mail. This means the FortiAuthenticator
itself must have working outbound SMTP before any API key can be issued.

### 2. `POST /localusers/` can return a list instead of a dict

The documentation describes a single created-user dict, but the actual response
is sometimes a one-element list. The client normalises this and falls back to
`GET /localusers/?username__exact=X` if `resource_uri` is missing from the
immediate POST response.

### 3. Available tokens can be `locked: true`

See the token pool section above. The filter is in `user-add._select_available_token`.

### 4. Race between `POST /localusers/` and the FTM activation mail

First-time user creation may return `400 {"error": "Failed to send
FortiToken Mobile activation message"}` while the mail still goes out. The
CLI rolls back the half-created user and exits non-zero. The second attempt
(usually immediately after) succeeds. If the first attempt *did* email, the
second attempt produces a duplicate mail - harmless but worth noting to the
end user.

### 5. `user_groups` on `/localusers/` is read-only

Group membership cannot be set at user creation time. Instead:

1. `POST /localusers/` - get the user URI
2. `POST /localgroup-memberships/` with `{user: <uri>, group: <uri>}` - one
   call per group

### 6. Mobile number format

Must be `+[country]-[number]`, for example `+46-701234567`. `+46701234567`
(no hyphen) and `070-1234567` (no country code) are both rejected. Validated
client-side before the request is sent.

## Secret storage

API keys live in the OS credential store, accessed through the `keyring`
library:

- macOS: Keychain
- Windows: Credential Manager
- Linux: Secret Service / libsecret

The config file only stores the service + account names pointing at the
keyring entries, never the keys themselves.

## Audit

Every write operation appends a JSONL line to
`<state_dir>/audit.log` with timestamp, user, host, command, and command
details (username, groups, customer code, ticket ID, selected token).

Customer code, ticket ID, and operator identity are also written to the
FortiAuthenticator user record via `custom1`, `custom2`, `custom3` - which
means the audit trail survives even if the local log is lost and the user
shows up in FortiAuthenticator's own logs with full provenance.

## Packaging

Ships as a PyInstaller single-file binary to sidestep:

- Python + virtualenv setup on target machines
- `pip install` permissions in restricted corporate environments
- Local policy blocking user-installed `.exe` wrappers (observed on Windows
  Server 2022)

GitHub Actions builds for macOS (arm64), Windows (x64) and Linux (x64) on
every `v*` tag and publishes them as Release assets.
