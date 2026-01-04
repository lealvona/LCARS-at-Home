#!/usr/bin/env python3
"""
LCARS Computer - Deployment Configuration Manager

This module handles infrastructure detection, service configuration,
and validation for both standard and custom deployment modes.
"""

import socket
import subprocess
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error
from urllib.parse import urlparse


@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    description: str
    default_host: str
    default_port: int
    health_check_url: str
    required: bool
    can_use_existing: bool
    detected_host: Optional[str] = None
    detected_port: Optional[int] = None
    use_existing: bool = False
    custom_host: Optional[str] = None
    custom_port: Optional[int] = None

    @property
    def effective_host(self) -> str:
        """Get the effective host to use."""
        # Always honor a user-specified host. This supports:
        # - connecting to existing/remote infrastructure
        # - running the installer against a non-local host (reporting/health checks)
        if self.custom_host:
            return self.custom_host

        # Detection is only relevant when the user is explicitly opting into an
        # existing service. If we're deploying new containers, "detected" values
        # (which reflect what's currently running) should not override defaults.
        if self.use_existing and self.detected_host:
            return self.detected_host

        return self.default_host

    @property
    def effective_port(self) -> int:
        """Get the effective port to use."""
        # `custom_port` is used in two scenarios:
        # 1) use_existing=True: user is pointing at a remote/existing service
        # 2) use_existing=False: user is deploying a new container but exposing a custom *host* port
        if self.custom_port:
            return self.custom_port
        elif self.detected_port:
            return self.detected_port
        return self.default_port

    @property
    def connection_string(self) -> str:
        """Get the connection string for this service."""
        return f"{self.effective_host}:{self.effective_port}"


# Default service configurations
DEFAULT_SERVICES = {
    "homeassistant": ServiceConfig(
        name="Home Assistant",
        description="State machine for device control",
        default_host="localhost",
        default_port=8123,
        health_check_url="http://{}:{}/api/",
        required=True,
        can_use_existing=True
    ),
    "postgres": ServiceConfig(
        name="PostgreSQL",
        description="Database for n8n workflows",
        default_host="localhost",
        default_port=5432,
        health_check_url="tcp://{}:{}",
        required=True,
        can_use_existing=True
    ),
    "redis": ServiceConfig(
        name="Redis",
        description="Task queue and caching",
        default_host="localhost",
        default_port=6379,
        health_check_url="tcp://{}:{}",
        required=False,
        can_use_existing=True
    ),
    "ollama": ServiceConfig(
        name="Ollama",
        description="Local LLM inference server",
        default_host="localhost",
        default_port=11434,
        health_check_url="http://{}:{}/api/tags",
        required=True,
        can_use_existing=True
    ),
    "n8n": ServiceConfig(
        name="n8n",
        description="Workflow orchestration",
        default_host="localhost",
        default_port=5678,
        health_check_url="http://{}:{}/healthz",
        required=True,
        can_use_existing=False  # n8n requires specific configuration
    ),
    "open-webui": ServiceConfig(
        name="Open WebUI",
        description="LLM chat interface",
        default_host="localhost",
        default_port=3000,
        # Prefer a real API endpoint (OpenAI-compatible) over a UI route.
        # This usually returns 200 or 401/403 when the service is up.
        health_check_url="http://{}:{}/v1/models",
        required=True,
        can_use_existing=True
    ),
    "whisper": ServiceConfig(
        name="Whisper STT",
        description="Speech-to-text service",
        default_host="localhost",
        default_port=10300,
        health_check_url="tcp://{}:{}",
        required=False,
        can_use_existing=True
    ),
    "piper": ServiceConfig(
        name="Piper TTS",
        description="Text-to-speech service",
        default_host="localhost",
        default_port=10200,
        health_check_url="tcp://{}:{}",
        required=False,
        can_use_existing=True
    ),
    "openwakeword": ServiceConfig(
        name="openWakeWord",
        description="Wake word detection",
        default_host="localhost",
        default_port=10400,
        health_check_url="tcp://{}:{}",
        required=False,
        can_use_existing=True
    ),
}


def check_port_available(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a port is open and accepting connections.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        True if port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.error:
        return False


def check_http_endpoint(url: str, timeout: float = 5.0) -> Tuple[bool, Optional[str]]:
    """
    Check if an HTTP endpoint is responding.

    Args:
        url: Full URL to check
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, error_message)
    """
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status < 500:
                return True, None
            else:
                return False, f"HTTP {response.status}"
    except urllib.error.HTTPError as e:
        # Some services return 401/403 when healthy but unauthorized
        if e.code in [401, 403, 404]:
            return True, None
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"Connection failed: {e.reason}"
    except Exception as e:
        return False, str(e)


def check_service_health(service: ServiceConfig) -> Tuple[bool, Optional[str]]:
    """
    Check if a service is healthy and responding.

    Args:
        service: Service configuration

    Returns:
        Tuple of (is_healthy, error_message)
    """
    host = service.effective_host
    port = service.effective_port

    # Allow users to paste a scheme in the host field (e.g. https://llm.example.com).
    # This keeps the UI as "hostname + port" while supporting HTTPS behind reverse proxies.
    scheme = "http"
    hostname = host
    if host.startswith("http://") or host.startswith("https://"):
        parsed = urlparse(host)
        if parsed.scheme:
            scheme = parsed.scheme
        if parsed.hostname:
            hostname = parsed.hostname

    # First check if port is open
    if not check_port_available(hostname, port):
        return False, f"Port {port} not accessible on {hostname}"

    # If health check URL is TCP-only, port check is sufficient
    if service.health_check_url.startswith("tcp://"):
        return True, None

    # Otherwise, check HTTP endpoint
    # Build the URL using the service's configured host/port, but with the scheme
    # derived from the user input (http/https). The templates in DEFAULT_SERVICES
    # are used only to provide the path.
    template_url = service.health_check_url.format("HOST", "PORT")
    parsed_template = urlparse(template_url)
    path = parsed_template.path or "/"
    if parsed_template.query:
        path = f"{path}?{parsed_template.query}"

    url = f"{scheme}://{hostname}:{port}{path}"
    return check_http_endpoint(url)


def detect_existing_services() -> Dict[str, ServiceConfig]:
    """
    Scan the local system for existing services that could be reused.

    Returns:
        Dictionary of detected services
    """
    detected = {}

    for key, service_template in DEFAULT_SERVICES.items():
        if not service_template.can_use_existing:
            detected[key] = service_template
            continue

        service = ServiceConfig(**asdict(service_template))

        # Check if service is running on default port
        if check_port_available(service.default_host, service.default_port):
            service.detected_host = service.default_host
            service.detected_port = service.default_port

            # Verify it's actually the expected service
            is_healthy, _ = check_service_health(service)
            if is_healthy:
                service.use_existing = False  # Let user decide

        detected[key] = service

    return detected


def check_docker_containers() -> Dict[str, Dict[str, Any]]:
    """
    Check for existing Docker containers that might be LCARS services.

    Returns:
        Dictionary of container information
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return {}

        containers = {}
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                container = json.loads(line)
                name = container.get('Names', '')

                # Check if this is an LCARS-related container
                if any(svc in name.lower() for svc in DEFAULT_SERVICES.keys()):
                    containers[name] = {
                        'id': container.get('ID'),
                        'status': container.get('Status'),
                        'state': container.get('State'),
                        'image': container.get('Image'),
                        'ports': container.get('Ports', ''),
                    }
            except json.JSONDecodeError:
                continue

        return containers

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}


def validate_port(port: Any) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate a port number.

    Args:
        port: Port value to validate

    Returns:
        Tuple of (is_valid, validated_port, error_message)
    """
    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            return False, None, "Port must be between 1 and 65535"
        return True, port_int, None
    except (ValueError, TypeError):
        return False, None, "Port must be a number"


def validate_hostname(hostname: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a hostname or IP address.

    Args:
        hostname: Hostname to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not hostname:
        return False, "Hostname cannot be empty"

    # Basic validation - allow localhost, IPs, hostnames
    if hostname in ['localhost', '127.0.0.1', '::1']:
        return True, None

    # Check if it's a valid IP or resolvable hostname
    try:
        socket.gethostbyname(hostname)
        return True, None
    except socket.gaierror:
        # Might be a hostname that doesn't resolve yet
        return True, None  # Allow it, but warn user


def generate_docker_compose_override(services: Dict[str, ServiceConfig]) -> str:
    """
    Generate a docker-compose override file based on service configuration.

    Args:
        services: Dictionary of service configurations

    Returns:
        YAML content for docker-compose override
    """
    # Services that should be disabled if using existing
    disabled_services: list[str] = []
    port_overrides: list[dict[str, Any]] = []

    for key, service in services.items():
        if service.use_existing and service.can_use_existing:
            disabled_services.append(key)
            continue

        if service.effective_port != service.default_port:
            port_overrides.append(
                {
                    'service': key,
                    'internal_port': service.default_port,
                    'external_port': service.effective_port,
                }
            )

    yaml_content = "# LCARS Computer - Deployment Configuration Override\n"
    yaml_content += "# Auto-generated - do not edit manually\n\n"
    yaml_content += "services:\n"

    # Disable services by assigning them to a non-default profile.
    # This makes `docker compose up -d` skip them unless `--profile disabled` is used.
    for service_key in disabled_services:
        yaml_content += f"  {service_key}:\n"
        yaml_content += "    profiles:\n"
        yaml_content += "      - disabled\n"

    # Handle n8n dependencies when postgres or redis are disabled
    # If postgres or redis are using existing services, we need to remove them
    # from n8n's depends_on to avoid "undefined service" errors
    if 'postgres' in disabled_services or 'redis' in disabled_services:
        yaml_content += "  n8n:\n"

        # Calculate remaining dependencies
        n8n_dependencies = []
        if 'postgres' not in disabled_services:
            n8n_dependencies.append('postgres')
        if 'redis' not in disabled_services:
            n8n_dependencies.append('redis')

        # Override depends_on
        if n8n_dependencies:
            yaml_content += "    depends_on:\n"
            for dep in n8n_dependencies:
                yaml_content += f"      - {dep}\n"
        else:
            # If all dependencies are disabled, set empty depends_on
            yaml_content += "    depends_on: []\n"

    # Add port overrides
    for override in port_overrides:
        yaml_content += f"  {override['service']}:\n"
        yaml_content += f"    ports:\n"
        yaml_content += f"      - \"{override['external_port']}:{override['internal_port']}\"\n"

    # Comment block for human readability
    if disabled_services:
        yaml_content += "\n# Disabled services (using existing infrastructure):\n"
        for service_key in disabled_services:
            yaml_content += f"# {service_key}: Using existing at {services[service_key].connection_string}\n"

    return yaml_content


def save_deployment_config(services: Dict[str, ServiceConfig], output_path: Path):
    """
    Save deployment configuration to a JSON file.

    Args:
        services: Service configurations
        output_path: Path to save configuration
    """
    config = {
        'version': '1.0',
        'services': {
            key: asdict(service) for key, service in services.items()
        }
    }

    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)


def load_deployment_config(config_path: Path) -> Optional[Dict[str, ServiceConfig]]:
    """
    Load deployment configuration from a JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        Dictionary of service configurations or None if file doesn't exist
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            data = json.load(f)

        services = {}
        for key, service_data in data.get('services', {}).items():
            services[key] = ServiceConfig(**service_data)

        return services
    except Exception:
        return None


if __name__ == '__main__':
    # Test detection
    print("Detecting existing services...")
    detected = detect_existing_services()

    for key, service in detected.items():
        if service.detected_port:
            print(f"✓ Found {service.name} at {service.connection_string}")
        else:
            print(f"✗ {service.name} not detected")

    print("\nChecking Docker containers...")
    containers = check_docker_containers()

    for name, info in containers.items():
        print(f"  {name}: {info['status']}")
