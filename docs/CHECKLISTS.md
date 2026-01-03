# Checklists

## Pre-flight (first deployment)

- [ ] Install Docker + Compose for your OS: [DOCKER_INSTALL.md](DOCKER_INSTALL.md)
- [ ] Run `python3 scripts/setup.py --generate-env` and set `HA_ACCESS_TOKEN`.
- [ ] Confirm `docker/.env` is not committed.
- [ ] Start stack (Linux): `cd docker && docker compose up -d`
- [ ] Start stack (Docker Desktop: Windows/macOS): `cd docker && docker compose -f docker-compose.desktop.yml up -d`
- [ ] Create HA admin + token.
- [ ] Import n8n workflows from `n8n/workflows/`.
- [ ] Configure n8n credential: Base URL `http://host.docker.internal:8123` + HA token header.
- [ ] Pull LLM model in Open WebUI/Ollama.

## Post-change verification

- [ ] `python3 scripts/health_check.py --verbose`
- [ ] Send a test webhook to n8n voice handler.
- [ ] Confirm HA received and spoke a response.

## Security quick scan

- [ ] No secrets in git (search for tokens/keys).
- [ ] No `:latest` tags in production (optional but recommended).
- [ ] Only necessary ports exposed.
