# Security Hardening Checklist

This is a pragmatic checklist for deploying the LCARS stack safely.

## Secrets

- Use `scripts/setup.py --generate-env` (or `scripts/deploy.sh`) to generate strong secrets.
- Do not commit `docker/.env`.
- Treat `N8N_ENCRYPTION_KEY` as **persistent**. Rotating it can break access to stored credentials.

## Docker installation

- Follow OS-appropriate install steps: [DOCKER_INSTALL.md](DOCKER_INSTALL.md)

## Network exposure

- Decide which services are LAN-accessible vs local-only.
- If you don’t need remote access, bind ports to localhost (example):
  - `127.0.0.1:5678:5678` (n8n)
  - `127.0.0.1:3000:8080` (Open WebUI)

## Home Assistant token scope

- Use a dedicated Long-Lived Access Token for n8n.
- Prefer minimal HA permissions if you use HA’s auth providers or proxy layers.

## Container privilege

- `homeassistant` is `privileged: true` in compose. Keep only if you require USB/Bluetooth access.
- Remove unneeded host mounts.

## Image pinning

- Avoid `:latest` in production.
- Pin versions and update intentionally.

## Backups

- Store backups outside the docker volumes directory.
- Test restore steps at least once.
