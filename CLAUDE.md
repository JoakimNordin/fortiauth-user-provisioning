# fauth - FortiAuthenticator user provisioning CLI

Public repo: https://github.com/JoakimNordin/fortiauth-user-provisioning

User-facing docs: [README.md](README.md) and [docs/DESIGN.md](docs/DESIGN.md).

## Snabbstart (utveckling)

```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
fauth --help
```

API-nycklar i OS credential store via `keyring`. Service-namnen styrs av
`config.toml` och dokumenteras i [README.md](README.md).

Cross-platform: macOS Keychain, Windows Credential Manager, Linux Secret Service.

## Designprinciper

Se [docs/DESIGN.md](docs/DESIGN.md) för fullständig design-rationale inklusive
FortiAuthenticator 8.0.0 API-quirks.

## Privata anteckningar

Projektplan, recon-data och fas-planer ligger i en privat Obsidian-vault
utanför detta repo - behövs inte för att bidra till publik kod.
