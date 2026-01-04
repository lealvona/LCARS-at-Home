#!/usr/bin/env python3
"""
LCARS Computer - System Health Check

This script verifies the health and connectivity of all components
in the LCARS Computer stack. It checks Docker containers, service
endpoints, and system resources.

Usage:
    python3 health_check.py [--verbose] [--json]

Options:
    --verbose    Show detailed output for each check
    --json       Output results in JSON format

Exit Codes:
    0  All systems operational
    1  One or more services have issues
    2  Critical failure (cannot reach essential services)
"""

import sys
import json
import socket
import argparse
import subprocess
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

# Attempt to import optional dependencies, providing fallbacks if unavailable.
# This approach allows the script to run on systems without requests installed.
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    import urllib.request
    import urllib.error


# Configuration for service endpoints. Each entry defines the container name,
# the URL to check, and the expected response criteria.
SERVICES = {
    "homeassistant": {
        "url": "http://localhost:8123/api/",
        "container": "LCARS-homeassistant",
        "port": 8123,
        "critical": True,
        "description": "Home Assistant - State Machine & Device Control"
    },
    "n8n": {
        "url": "http://localhost:5678/healthz",
        "container": "LCARS-n8n",
        "port": 5678,
        "critical": True,
        "description": "n8n - Workflow Orchestration Engine"
    },
    "open-webui": {
        "url": "http://localhost:3000/health",
        "container": "LCARS-open-webui",
        "port": 3000,
        "critical": True,
        "description": "Open WebUI - LLM Interface & RAG System"
    },
    "ollama": {
        "url": "http://localhost:11434/api/tags",
        "container": "LCARS-ollama",
        "port": 11434,
        "critical": True,
        "description": "Ollama - Local LLM Inference Server"
    },
    "whisper": {
        "url": "http://localhost:10300/",
        "container": "LCARS-whisper",
        "port": 10300,
        "critical": False,
        "description": "Whisper - Speech-to-Text (Wyoming)"
    },
    "piper": {
        "url": "http://localhost:10200/",
        "container": "LCARS-piper",
        "port": 10200,
        "critical": False,
        "description": "Piper - Text-to-Speech (Wyoming)"
    },
    "openwakeword": {
        "url": None,  # No HTTP endpoint, check port only
        "container": "LCARS-openwakeword",
        "port": 10400,
        "critical": False,
        "description": "openWakeWord - Wake Word Detection"
    },
    "postgres": {
        "url": None,
        "container": "LCARS-postgres",
        "port": 5432,
        "critical": True,
        "description": "PostgreSQL - Workflow Database"
    },
    "redis": {
        "url": None,
        "container": "LCARS-redis",
        "port": 6379,
        "critical": False,
        "description": "Redis - Task Queue & Caching"
    }
}


@dataclass
class ServiceStatus:
    """Represents the health status of a single service."""
    name: str
    description: str
    container_running: bool
    port_open: bool
    http_ok: Optional[bool]
    response_time_ms: Optional[float]
    error_message: Optional[str]
    critical: bool
    
    @property
    def healthy(self) -> bool:
        """A service is healthy if container is running and port is accessible."""
        return self.container_running and self.port_open


@dataclass
class SystemStatus:
    """Represents the overall system health status."""
    timestamp: str
    all_healthy: bool
    critical_healthy: bool
    services: dict
    system_resources: dict
    llm_models: list


class TerminalColors:
    """ANSI color codes for terminal output, providing visual feedback."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Disable colors for non-TTY output (like piping to a file)."""
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.RED = ''
        cls.BLUE = ''
        cls.BOLD = ''
        cls.END = ''


def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a TCP port is open and accepting connections.
    
    This function attempts to establish a TCP connection to the specified
    host and port. A successful connection indicates the service is listening.
    
    Args:
        host: The hostname or IP address to check
        port: The TCP port number
        timeout: Connection timeout in seconds
    
    Returns:
        True if the port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.error:
        return False


def check_http_endpoint(url: str, timeout: float = 5.0) -> tuple[bool, float, str]:
    """
    Check if an HTTP endpoint is responding.
    
    This function sends a GET request to the URL and checks for a successful
    response (status code < 500). It measures response time for performance
    monitoring.
    
    Args:
        url: The full URL to check
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (success, response_time_ms, error_message)
    """
    start_time = datetime.now()
    
    if REQUESTS_AVAILABLE:
        # Use the requests library if available (more feature-rich)
        try:
            response = requests.get(url, timeout=timeout)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            if response.status_code < 500:
                return True, elapsed, None
            else:
                return False, elapsed, f"HTTP {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, 0, "Connection refused"
        except requests.exceptions.Timeout:
            return False, timeout * 1000, "Timeout"
        except Exception as e:
            return False, 0, str(e)
    else:
        # Fall back to urllib if requests is not installed
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                if response.status < 500:
                    return True, elapsed, None
                else:
                    return False, elapsed, f"HTTP {response.status}"
        except urllib.error.URLError as e:
            return False, 0, str(e.reason)
        except Exception as e:
            return False, 0, str(e)


def check_container_running(container_name: str) -> bool:
    """
    Check if a Docker container is running.
    
    Uses docker inspect to query the container's state. This is more reliable
    than parsing docker ps output.
    
    Args:
        container_name: Name of the Docker container
    
    Returns:
        True if container is running, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip().lower() == "true"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_system_resources() -> dict:
    """
    Gather system resource information (RAM, CPU, disk).
    
    This provides context for troubleshooting performance issues,
    especially important for LLM inference which is resource-intensive.
    
    Returns:
        Dictionary containing memory, disk, and CPU information
    """
    resources = {}
    
    # Check available memory using /proc/meminfo (Linux-specific)
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        mem_total = mem_available = 0
        for line in meminfo.split('\n'):
            if line.startswith('MemTotal:'):
                mem_total = int(line.split()[1]) / 1024 / 1024  # Convert to GB
            elif line.startswith('MemAvailable:'):
                mem_available = int(line.split()[1]) / 1024 / 1024
        
        resources['memory'] = {
            'total_gb': round(mem_total, 1),
            'available_gb': round(mem_available, 1),
            'used_percent': round((1 - mem_available / mem_total) * 100, 1) if mem_total > 0 else 0
        }
    except Exception:
        resources['memory'] = {'error': 'Unable to read memory info'}
    
    # Check disk space using df command
    try:
        result = subprocess.run(
            ['df', '-BG', '/'],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            resources['disk'] = {
                'total_gb': int(parts[1].rstrip('G')),
                'available_gb': int(parts[3].rstrip('G')),
                'used_percent': int(parts[4].rstrip('%'))
            }
    except Exception:
        resources['disk'] = {'error': 'Unable to read disk info'}
    
    # Check for NVIDIA GPU
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            resources['gpu'] = {
                'name': parts[0],
                'memory_used_mb': int(parts[1]),
                'memory_total_mb': int(parts[2]),
                'utilization_percent': int(parts[3])
            }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        resources['gpu'] = None  # No GPU or nvidia-smi not available
    
    return resources


def get_ollama_models() -> list:
    """
    Get list of LLM models available in Ollama.
    
    This helps verify that the required models for the LCARS computer
    are downloaded and available.
    
    Returns:
        List of model names, or empty list if Ollama is unavailable
    """
    try:
        if REQUESTS_AVAILABLE:
            response = requests.get('http://localhost:11434/api/tags', timeout=5)
            data = response.json()
        else:
            with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5) as response:
                data = json.loads(response.read().decode())
        
        models = []
        for model in data.get('models', []):
            name = model.get('name', 'unknown')
            size = model.get('size', 0)
            size_gb = round(size / (1024**3), 1) if size else 0
            models.append({'name': name, 'size_gb': size_gb})
        return models
    except Exception:
        return []


def check_service(name: str, config: dict) -> ServiceStatus:
    """
    Perform a comprehensive health check on a single service.
    
    This function checks container status, port accessibility, and
    HTTP endpoint (if applicable). It compiles all results into
    a ServiceStatus object.
    
    Args:
        name: Service identifier
        config: Service configuration dictionary
    
    Returns:
        ServiceStatus object with all check results
    """
    # Check if the container is running
    container_running = check_container_running(config['container'])
    
    # Check if the port is open
    port_open = check_port('localhost', config['port'])
    
    # Check HTTP endpoint if configured
    http_ok = None
    response_time = None
    error_msg = None
    
    if config.get('url'):
        http_ok, response_time, error_msg = check_http_endpoint(config['url'])
    
    return ServiceStatus(
        name=name,
        description=config['description'],
        container_running=container_running,
        port_open=port_open,
        http_ok=http_ok,
        response_time_ms=round(response_time, 1) if response_time else None,
        error_message=error_msg,
        critical=config['critical']
    )


def run_health_check(verbose: bool = False) -> SystemStatus:
    """
    Run a complete health check on all LCARS Computer services.
    
    This is the main entry point for the health check. It iterates through
    all configured services, checks their status, and compiles a comprehensive
    system status report.
    
    Args:
        verbose: If True, print detailed status as checks run
    
    Returns:
        SystemStatus object containing complete system health information
    """
    services_status = {}
    all_healthy = True
    critical_healthy = True
    
    if verbose:
        print(f"\n{TerminalColors.BOLD}Running LCARS Computer Health Check...{TerminalColors.END}\n")
    
    for name, config in SERVICES.items():
        if verbose:
            print(f"Checking {name}...", end=" ")
        
        status = check_service(name, config)
        services_status[name] = asdict(status)
        
        if not status.healthy:
            all_healthy = False
            if status.critical:
                critical_healthy = False
        
        if verbose:
            if status.healthy:
                print(f"{TerminalColors.GREEN}✓ OK{TerminalColors.END}")
            else:
                print(f"{TerminalColors.RED}✗ FAILED{TerminalColors.END}")
                if status.error_message:
                    print(f"  Error: {status.error_message}")
    
    # Gather additional system information
    system_resources = get_system_resources()
    llm_models = get_ollama_models()
    
    return SystemStatus(
        timestamp=datetime.now().isoformat(),
        all_healthy=all_healthy,
        critical_healthy=critical_healthy,
        services=services_status,
        system_resources=system_resources,
        llm_models=llm_models
    )


def print_status_report(status: SystemStatus):
    """
    Print a formatted status report to the terminal.
    
    This provides a human-readable summary of the system health,
    with color-coded status indicators and resource usage.
    
    Args:
        status: The SystemStatus object to display
    """
    c = TerminalColors
    
    print(f"\n{c.BOLD}{'='*60}{c.END}")
    print(f"{c.BOLD}         LCARS COMPUTER SYSTEM STATUS REPORT{c.END}")
    print(f"{c.BOLD}{'='*60}{c.END}\n")
    
    # Overall status
    if status.all_healthy:
        print(f"Overall Status: {c.GREEN}ALL SYSTEMS OPERATIONAL{c.END}")
    elif status.critical_healthy:
        print(f"Overall Status: {c.YELLOW}DEGRADED - Non-critical services down{c.END}")
    else:
        print(f"Overall Status: {c.RED}CRITICAL - Essential services unavailable{c.END}")
    
    print(f"Timestamp: {status.timestamp}\n")
    
    # Service status table
    print(f"{c.BOLD}Services:{c.END}\n")
    print(f"  {'Service':<20} {'Container':<12} {'Port':<8} {'HTTP':<10} {'Latency':<10}")
    print(f"  {'-'*18:<20} {'-'*10:<12} {'-'*6:<8} {'-'*8:<10} {'-'*8:<10}")
    
    for name, svc in status.services.items():
        container_status = f"{c.GREEN}Running{c.END}" if svc['container_running'] else f"{c.RED}Stopped{c.END}"
        port_status = f"{c.GREEN}Open{c.END}" if svc['port_open'] else f"{c.RED}Closed{c.END}"
        
        if svc['http_ok'] is None:
            http_status = "N/A"
        elif svc['http_ok']:
            http_status = f"{c.GREEN}OK{c.END}"
        else:
            http_status = f"{c.RED}Failed{c.END}"
        
        latency = f"{svc['response_time_ms']:.0f}ms" if svc['response_time_ms'] else "N/A"
        
        # Account for ANSI codes in column width calculations
        print(f"  {name:<20} {container_status:<21} {port_status:<17} {http_status:<19} {latency:<10}")
    
    # System resources
    print(f"\n{c.BOLD}System Resources:{c.END}\n")
    
    mem = status.system_resources.get('memory', {})
    if 'error' not in mem:
        mem_color = c.GREEN if mem['used_percent'] < 80 else (c.YELLOW if mem['used_percent'] < 90 else c.RED)
        print(f"  Memory: {mem_color}{mem['used_percent']}%{c.END} used ({mem['available_gb']}GB available of {mem['total_gb']}GB)")
    
    disk = status.system_resources.get('disk', {})
    if 'error' not in disk:
        disk_color = c.GREEN if disk['used_percent'] < 80 else (c.YELLOW if disk['used_percent'] < 90 else c.RED)
        print(f"  Disk:   {disk_color}{disk['used_percent']}%{c.END} used ({disk['available_gb']}GB available)")
    
    gpu = status.system_resources.get('gpu')
    if gpu:
        gpu_mem_pct = round(gpu['memory_used_mb'] / gpu['memory_total_mb'] * 100)
        gpu_color = c.GREEN if gpu_mem_pct < 80 else (c.YELLOW if gpu_mem_pct < 95 else c.RED)
        print(f"  GPU:    {gpu['name']}")
        print(f"          VRAM: {gpu_color}{gpu_mem_pct}%{c.END} ({gpu['memory_used_mb']}MB / {gpu['memory_total_mb']}MB)")
        print(f"          Utilization: {gpu['utilization_percent']}%")
    else:
        print(f"  GPU:    {c.YELLOW}Not detected or nvidia-smi unavailable{c.END}")
    
    # LLM Models
    print(f"\n{c.BOLD}Available LLM Models:{c.END}\n")
    if status.llm_models:
        for model in status.llm_models:
            print(f"  • {model['name']} ({model['size_gb']}GB)")
    else:
        print(f"  {c.YELLOW}No models found. Pull a model with: docker exec LCARS-ollama ollama pull llama3.1:8b{c.END}")
    
    print(f"\n{c.BOLD}{'='*60}{c.END}\n")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='LCARS Computer System Health Check',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output for each check')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output results in JSON format')
    
    args = parser.parse_args()
    
    # Disable colors if outputting JSON or not connected to a terminal
    if args.json or not sys.stdout.isatty():
        TerminalColors.disable()
    
    # Run the health check
    status = run_health_check(verbose=args.verbose and not args.json)
    
    # Output results
    if args.json:
        print(json.dumps(asdict(status), indent=2))
    else:
        print_status_report(status)
    
    # Set exit code based on status
    if not status.critical_healthy:
        sys.exit(2)
    elif not status.all_healthy:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
