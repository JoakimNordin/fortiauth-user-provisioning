# fauth - FortiAuthenticator user provisioning CLI

Projektbeskrivning, design och Fas 1-plan finns i Obsidian-vaulten:

- `~/obsidian-vault/projects/fortiauth-user-provisioning.md` - projektnot
- `~/obsidian-vault/projects/fortiauth-user-provisioning/design.md` - designbeslut + API-recon
- `~/obsidian-vault/projects/fortiauth-user-provisioning/fas1-implementation-plan.md` - impl-ordning

Recon-data (utanför vault): `~/work/research/fortiauth-recon/out/*.json`

## Snabbstart

```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
fauth --help
```

API-nycklar i macOS Keychain:
- `fauth-example-ro` / `api_readonly` (read-only, för läskommandon)
- `fauth-example-rw` / `fauth-cli` (read+write, för skrivkommandon)

## Designprinciper

- CLI-first, manuell input (ärendesystem Rutin kan inte trigga externt)
- MFA default på (FTM med email-aktivering) - `--no-mfa` för service-konton
- Token-pool-kontroll: varna < 3 lediga, blockera vid 0
- Audit via `custom1` (kundkod), `custom2` (ticket-ID), `custom3` (`fauth-cli:<user@host>`)
- Ingen klartext-nyckel i kod eller config - alltid Keychain

## Api-referens

FortiAuthenticator 8.0.0 REST API v1, basauth. Se `design.md` för schema + flöden.
