# Custom Deployment Guide

## Overview

The LCARS Computer installation system now supports two deployment modes:

1. **Standard Deployment**: Quick setup with all defaults
2. **Custom Deployment**: Advanced configuration with infrastructure detection and reuse

## Deployment Modes

### Standard Deployment

**Best for:** New installations, testing, or users who want the fastest setup.

**Features:**
- All services deployed as fresh Docker containers
- Default ports used for all services
- No manual configuration required
- Approximately 10-15 minutes total setup time

**Services Deployed:**
- Home Assistant (port 8123)
- PostgreSQL (port 5432)
- Redis (port 6379)
- Ollama (port 11434)
- n8n (port 5678)
- Open WebUI (port 3000)
- Whisper STT (port 10300)
- Piper TTS (port 10200)
- openWakeWord (port 10400)

### Custom Deployment

**Best for:** Advanced users, production environments, or systems with existing infrastructure.

**Features:**
- Automatic detection of existing services
- Reuse existing databases, LLM servers, etc.
- Custom port mapping for all services
- Health checking before deployment
- Service-by-service configuration

**Benefits:**
- Reduce resource usage by reusing existing services
- Avoid port conflicts on busy servers
- Integrate with existing infrastructure
- Greater control over deployment

## Custom Deployment Workflow

### Step 1: Infrastructure Detection

The system automatically scans for:
- Existing services running on default ports
- Docker containers that might be LCARS-related
- Port availability

Example detection output:
```
✓ Found PostgreSQL at localhost:5432
✓ Found Ollama at localhost:11434
✗ Home Assistant not detected
```

### Step 2: Service Configuration

For each service, you can:

1. **Connect to Existing/Remote Server**
   - Check "Connect to existing/remote [service name] server"
   - Specify hostname/IP address (e.g., 'db.example.com', '192.168.1.100', 'host.docker.internal')
   - Specify port number
   - Test connection with health check
   - Override health check if infrastructure not ready yet
   - Supports local, remote, and 3rd-party servers

2. **Deploy New Container**
   - Uncheck the "Connect to existing/remote" checkbox
   - Container hostname is automatically set (e.g., 'postgres', 'ollama')
   - Specify external port mapping (defaults shown)
   - Service will be deployed fresh in Docker

### Step 3: Validation

Before deployment, the system:
- Validates all hostnames and ports
- Health checks all existing services
- Allows manual override if needed
- Saves configuration for future reference

### Step 4: Deployment

The system generates:
- Custom `docker-compose` override file
- Deployment configuration JSON
- Modified environment variables

Only required containers are deployed, others connect to existing infrastructure.

## Service-Specific Notes

### Can Use Existing Infrastructure

These services can connect to existing instances:
- **PostgreSQL**: Any PostgreSQL 14+ database
- **Redis**: Any Redis 6+ instance
- **Ollama**: Existing Ollama server with models
- **Home Assistant**: Existing HA instance (requires configuration sync)
- **Open WebUI**: Existing Open WebUI instance
- **Whisper/Piper**: Existing Wyoming protocol services

### Must Deploy Fresh

These services require LCARS-specific configuration:
- **n8n**: Requires LCARS workflows and integrations

## Health Check Details

The system performs health checks using:

### HTTP Services
- **URL**: Service-specific endpoint (e.g., `/api/`, `/health`)
- **Method**: GET request with 5-second timeout
- **Success**: HTTP status < 500
- **Notes**: 401/403/404 considered healthy (authentication required)

### TCP Services
- **Method**: Socket connection test
- **Timeout**: 2 seconds
- **Success**: Port accepting connections

## Configuration Files

Custom deployment creates:

### `docker/deployment_config.json`
Stores the full deployment configuration including:
- Service hosts and ports
- Which services use existing infrastructure
- Custom port mappings

Example:
```json
{
  "version": "1.0",
  "services": {
    "postgres": {
      "name": "PostgreSQL",
      "use_existing": true,
      "custom_host": "192.168.1.100",
      "custom_port": 5432
    },
    "homeassistant": {
      "name": "Home Assistant",
      "use_existing": false,
      "custom_port": 8123
    }
  }
}
```

### `docker-compose.override.yml` (generated)
Overrides default compose configuration with custom ports.

## Port Customization

### Default Ports

| Service | Default Port | Can Change |
|---------|--------------|------------|
| Home Assistant | 8123 | ✅ |
| PostgreSQL | 5432 | ✅ |
| Redis | 6379 | ✅ |
| Ollama | 11434 | ✅ |
| n8n | 5678 | ✅ |
| Open WebUI | 3000 | ✅ |
| Whisper | 10300 | ✅ |
| Piper | 10200 | ✅ |
| openWakeWord | 10400 | ✅ |

### Port Conflict Resolution

If the system detects a port conflict:
1. The service will be marked as "detected"
2. You can choose to use the existing service
3. Or deploy to a different port

## Using Existing PostgreSQL

To use an existing PostgreSQL instance:

1. Enable "Use existing PostgreSQL"
2. Enter host and port
3. Click "Test Connection"
4. Update `.env` file with credentials:
   ```bash
   POSTGRES_PASSWORD=your_existing_db_password
   ```

The n8n container will connect to your existing database instead of deploying a new one.

## Using Existing Ollama

To use an existing Ollama server:

1. Enable "Use existing Ollama"
2. Enter host and port (e.g., `192.168.1.50:11434`)
3. Test connection
4. Ensure required models are pulled:
   ```bash
   ollama pull llama3.1:8b
   ```

The LCARS system will connect to your existing Ollama server.

## Force Using Unresponsive Services

If you're planning to set up infrastructure later:

1. Enter host and port details
2. Click "Test Connection"
3. When it fails, check "Use this service anyway"
4. The service will be configured despite health check failure

This is useful when:
- Setting up configuration before infrastructure is ready
- Testing deployment in staging environments
- Infrastructure is behind firewalls during setup

## Troubleshooting

### "Service not detected" despite being running

**Cause**: Firewall, wrong port, or service not responding to health checks

**Solution**:
1. Manually specify host and port
2. Test connection
3. Check firewall rules
4. Verify service is listening on expected interface

### "Connection failed: Connection refused"

**Cause**: Service not running or port blocked

**Solution**:
1. Verify service is running: `sudo systemctl status <service>`
2. Check port is open: `netstat -tlnp | grep <port>`
3. Test locally: `curl http://localhost:<port>`

### Custom port not applied

**Cause**: Configuration not saved or override file not loaded

**Solution**:
1. Verify `deployment_config.json` exists in `docker/`
2. Check `docker-compose.override.yml` was generated
3. Restart deployment: `docker compose down && docker compose up -d`

## Best Practices

### For Production

1. Use existing PostgreSQL with regular backups
2. Use existing Redis for better performance monitoring
3. Deploy Ollama on dedicated GPU server
4. Use custom ports to avoid conflicts
5. Enable all health checks

### For Development

1. Standard deployment for fastest setup
2. Use custom ports if running multiple instances
3. Reuse Ollama to save disk space (models are large)

### For Testing

1. Standard deployment in isolated environment
2. Use default ports for simplicity
3. Clean slate for each test run

## Security Considerations

### External Services

When connecting to external services:
- Use strong passwords
- Enable TLS/SSL when available
- Restrict network access with firewalls
- Use VLANs to segregate traffic

### Port Exposure

- Only expose ports on localhost unless needed
- Use reverse proxy (nginx/Traefik) for external access
- Enable authentication on all services

### Credentials

- Never commit `deployment_config.json` to version control
- Rotate passwords regularly
- Use separate credentials for each environment

## Migration Guide

### From Standard to Custom

1. Stop all services: `cd docker && docker compose down`
2. Backup data: `./scripts/backup.py`
3. Run custom deployment in Streamlit guide
4. Configure services to use existing data volumes
5. Deploy with custom configuration

### From Custom to Standard

1. Export important data (workflows, configurations)
2. Run `docker compose down` to stop custom deployment
3. Remove `deployment_config.json`
4. Run standard deployment
5. Re-import data

## Example Scenarios

### Scenario 1: Existing Database Server

**Situation**: You have a PostgreSQL server running on `192.168.1.10:5432`

**Steps**:
1. Select Custom Deployment
2. Scan for services
3. Enable "Use existing PostgreSQL"
4. Enter `192.168.1.10` as host
5. Test connection
6. Deploy remaining services

### Scenario 2: Port Conflict on 8123

**Situation**: Another service is using port 8123

**Steps**:
1. Select Custom Deployment
2. For Home Assistant, uncheck "Use existing"
3. Set custom port to `18123`
4. Update firewall rules if needed
5. Access Home Assistant at `http://localhost:18123`

### Scenario 3: Centralized LLM Server

**Situation**: Running Ollama on a GPU server at `gpu-server:11434`

**Steps**:
1. Select Custom Deployment
2. Enable "Use existing Ollama"
3. Enter `gpu-server` as host, `11434` as port
4. Test connection
5. Verify models are available
6. Deploy other services

## API Reference

The deployment configuration module (`deploy_config.py`) provides:

### Functions

- `detect_existing_services()`: Scan for running services
- `check_service_health(service)`: Test service connectivity
- `check_port_available(host, port)`: Test port accessibility
- `validate_hostname(hostname)`: Validate hostname format
- `validate_port(port)`: Validate port number
- `save_deployment_config(services, path)`: Save configuration
- `load_deployment_config(path)`: Load saved configuration

### Classes

- `ServiceConfig`: Configuration for a single service
  - Properties: `effective_host`, `effective_port`, `connection_string`
  - Methods: None (dataclass)

## Support

For issues with custom deployment:

1. Check logs: `logs/install_*.log`
2. Review configuration: `docker/deployment_config.json`
3. Test services individually
4. Consult main documentation: `README.md`
5. Report issues on GitHub

Live long and prosper. 🖖
