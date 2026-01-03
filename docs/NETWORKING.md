# Networking Notes

This repo uses a mixed networking setup:

- `homeassistant` runs with `network_mode: host` (for mDNS / discovery / some hardware scenarios).
- Other services run on the `lcars_network` bridge network.

## Key implication

Other containers cannot reliably reach Home Assistant via compose DNS name `homeassistant`.

## Correct way for containers to reach Home Assistant

Use:

- `http://host.docker.internal:8123`

In n8n, workflows use the `HA_URL` environment variable (defaulting to the value above).

On Linux, containers do not always have `host.docker.internal` by default, so `docker/docker-compose.yml` adds:

- `extra_hosts: ["host.docker.internal:host-gateway"]` (at least for `n8n`)

## Home Assistant to container reachability

Home Assistant config calls n8n and Open WebUI using `host.docker.internal`:

- n8n webhook: `http://host.docker.internal:5678/webhook/voice-command`
- Open WebUI API: `http://host.docker.internal:3000/...`

This works because Home Assistant is effectively on the host network.

## If you want everything on the bridge network

Alternative design (not implemented here): remove `network_mode: host` and run HA on `lcars_network` with specific port mappings and mDNS solutions.

### Docker Desktop (Windows/macOS)

Docker Desktop has limitations for `network_mode: host`. Use the override compose file:

- [docker/docker-compose.desktop.yml](../docker/docker-compose.desktop.yml)

That is a larger change; current repo keeps host-networking for HA.
