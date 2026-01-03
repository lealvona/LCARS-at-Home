# Ops Runbook

Prerequisites:

- Install Docker + Compose for your OS: [DOCKER_INSTALL.md](DOCKER_INSTALL.md)

## Start / Stop

- Start (Linux): `cd docker && docker compose up -d`
- Start (Docker Desktop: Windows/macOS): `cd docker && docker compose -f docker-compose.desktop.yml up -d`
- Stop: `cd docker && docker compose down`
- Logs: `cd docker && docker compose logs -f`

## Health

- Run: `python3 scripts/health_check.py --verbose`

What it checks:

- Containers running
- Ports open
- HTTP endpoints responding (where applicable)

## Common issues

### n8n cannot reach Home Assistant

Symptoms:

- n8n HTTP Request nodes fail with connection errors.

Fix:

- Ensure URLs in workflows use `http://host.docker.internal:8123`.
- Ensure `n8n` has `extra_hosts: ["host.docker.internal:host-gateway"]` on Linux.

### Slow responses

- Check whether Ollama is using GPU.
- Consider quantized models.
- Reduce context size.

## Backup / Restore

- Backup: `python3 scripts/backup.py --compress --output backups --keep 5`
- Restore: (document your restore procedure here once you confirm your desired rollback strategy)

## Upgrade

- Use `scripts/update.sh`.
- Prefer pinning images before production use.
