# Data Protection Rules

> These rules are loaded by `steps/context-loader.md` at the start of every command.
> AI agents MUST follow these rules without exception.

---

## NEVER Read — Sensitive Files

The following file patterns contain credentials, secrets, or private keys.
**Do NOT read, display, log, or reference their contents under any circumstance.**

### Environment & Secrets
- `.env`
- `.env.*` (e.g., `.env.local`, `.env.production`, `.env.staging`)
- `*credentials*`

### Cryptographic Keys & Certificates
- `*.key`
- `*.pem`
- `*.p12`
- `*.pfx`
- `*.jks`
- `*.keystore`
- `*.crt` / `*.cert`

### Framework-Specific Config Files (may contain DB passwords, API keys)
- `application-prod.yml` / `application-prod.properties`
- `application-production.yml`
- `appsettings.Production.json`
- `appsettings.Staging.json`
- `database.yml` (Rails)
- `config/master.key` (Rails)
- `storage/oauth-private.key`

### Files Matching Dangerous Keywords
Any file whose name contains (case-insensitive):
- `password`
- `passwd`
- `secret`
- `private_key`
- `api_key`
- `access_token`
- `auth_token`

---

## NEVER Write or Modify

- Any file listed above
- `*.lock` files that are not package lock files (e.g., `*.lock` outside of `package-lock.json`, `yarn.lock`, `composer.lock`)

---

## NEVER Execute via Bash

- Commands that print secrets: `printenv`, `env | grep -i secret`, `cat .env`
- Commands that expose credentials: `docker inspect`, `kubectl get secret -o yaml`
- Git commands that may expose history of secrets: `git show`, `git log -p` on config files

---

## Safe Alternatives

If context about environment configuration is needed:

1. Ask the user to describe the configuration **without sharing actual values**.
2. Reference the **structure** of config (keys, not values): "I see you use `DATABASE_URL` — I'll generate code that reads from that variable."
3. Use placeholder values in generated code: `process.env.DATABASE_URL` or `${DATABASE_URL}`.

---

## If a Sensitive File is Accidentally Accessed

1. Do NOT display or repeat any content from the file.
2. Immediately stop and notify the user: "I've detected a sensitive file. I will not read or use its contents."
3. Ask the user what they actually need (usually it's the structure, not the values).
