#!/usr/bin/env python3
"""
LCARS Computer - Interactive Installation Guide
A robust, production-grade installation system with real-time execution,
comprehensive logging, and excellent user experience.
"""

import streamlit as st
import subprocess
import threading
import queue
import copy
import re
import os
import sys
import platform
import time
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
import json

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.resolve()
DOCKER_DIR = PROJECT_ROOT / "docker"
LOG_DIR = PROJECT_ROOT / "logs"
INSTALL_LOG = LOG_DIR / f"install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)

# Navigation constants with icons
NAV_ITEMS = [
    ("🏠", "Welcome", "Overview of the LCARS Computer system"),
    ("🔍", "Pre-Flight Check", "Verify system requirements"),
    ("🐳", "Docker Setup", "Install Docker and prerequisites"),
    ("⚙️", "Configuration", "Generate secure credentials"),
    ("🚀", "Deployment", "Deploy the container stack"),
    ("🔗", "Integration", "Connect services together"),
    ("✅", "Verification", "Test system health"),
    ("🎮", "Operations", "Daily usage and management"),
]

HEALTH_CHECK_SERVICE_KEYS = [
    "homeassistant",
    "n8n",
    "open-webui",
    "ollama",
    "whisper",
    "piper",
]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def log_message(message: str, level: str = "INFO"):
    """Write a message to the installation log file and CLI log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"

    with open(INSTALL_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

    # Add to CLI log in session state
    if 'cli_log' in st.session_state:
        st.session_state.cli_log.append({
            'timestamp': timestamp,
            'level': level,
            'message': message
        })

def init_session_state():
    """Initialize session state variables."""
    if 'installation_progress' not in st.session_state:
        st.session_state.installation_progress = {}
    if 'command_output' not in st.session_state:
        st.session_state.command_output = {}
    if 'environment_vars' not in st.session_state:
        st.session_state.environment_vars = {}
    if 'deployment_mode' not in st.session_state:
        st.session_state.deployment_mode = None
    if 'deployment_config' not in st.session_state:
        st.session_state.deployment_config = None
    if 'deployment_service_health' not in st.session_state:
        st.session_state.deployment_service_health = {}
    if 'deployment_last_discovery' not in st.session_state:
        st.session_state.deployment_last_discovery = None
    if 'cli_log' not in st.session_state:
        st.session_state.cli_log = []

def execute_command_with_output(command: str | List[str], shell: bool = True, cwd: Optional[Path] = None) -> Tuple[int, str]:
    """
    Execute a shell command and capture output in real-time.
    Returns (return_code, combined_output).
    """
    log_message(f"Executing command: {command}")

    try:
        effective_shell = shell
        if isinstance(command, list):
            effective_shell = False

        if platform.system() == "Windows" and effective_shell:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                bufsize=1,
                universal_newlines=True
            )
        else:
            process = subprocess.Popen(
                command,
                shell=effective_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                bufsize=1,
                universal_newlines=True
            )

        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            log_message(line.strip(), "COMMAND_OUTPUT")

        process.wait()
        combined_output = "".join(output_lines)

        log_message(f"Command completed with return code: {process.returncode}")
        return process.returncode, combined_output

    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        log_message(error_msg, "ERROR")
        return 1, error_msg

def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["where", command], capture_output=True)
        else:
            result = subprocess.run(["which", command], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False

def generate_secure_secret(length: int = 32) -> str:
    """Generate a cryptographically secure random hex string."""
    return secrets.token_hex(length)

def generate_secure_password(length: int = 24) -> str:
    """Generate a secure password."""
    return secrets.token_urlsafe(length)


def upsert_env_var(env_path: Path, key: str, value: str) -> None:
    """Insert or update KEY=VALUE in a .env-style file."""
    key_prefix = f"{key}="
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        lines = content.splitlines()
    else:
        lines = []

    replaced = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith(key_prefix):
            new_lines.append(f"{key}={value}")
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        if new_lines and new_lines[-1].strip() != "":
            new_lines.append("")
        new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _load_deploy_config_module():
    """Import scripts/deploy_config.py at runtime so the guide can run standalone."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        import deploy_config  # type: ignore
    except Exception:
        return None
    return deploy_config


def _load_service_configs():
    """Load service configs from docker/deployment_config.json if present; else defaults."""
    deploy_config = _load_deploy_config_module()
    if deploy_config is None:
        return None, None

    # Prefer in-session config (e.g., immediately after edits) if available.
    services = st.session_state.get("deployment_config")
    if services:
        return deploy_config, services

    config_path = DOCKER_DIR / "deployment_config.json"
    loaded = deploy_config.load_deployment_config(config_path)
    if loaded:
        return deploy_config, loaded

    return deploy_config, copy.deepcopy(deploy_config.DEFAULT_SERVICES)


def _format_base_url(host: str, port: int) -> str:
    """Format a base URL from a host (optionally including scheme) and port."""
    from urllib.parse import urlparse

    if host.startswith("http://") or host.startswith("https://"):
        parsed = urlparse(host)
        scheme = parsed.scheme or "http"
        hostname = parsed.hostname or host
        return f"{scheme}://{hostname}:{port}"

    return f"http://{host}:{port}"

# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_header():
    """Render the LCARS-themed header."""
    st.markdown("""
        <style>
        .lcars-header {
            background: linear-gradient(135deg, #1a0033 0%, #330066 100%);
            border-left: 8px solid #FF9900;
            border-radius: 0 20px 20px 0;
            padding: 20px;
            margin-bottom: 30px;
        }
        .lcars-title {
            color: #CC99CC;
            font-size: 2.5em;
            font-weight: bold;
            margin: 0;
            font-family: 'Arial', sans-serif;
        }
        .lcars-subtitle {
            color: #FF9900;
            font-size: 1.2em;
            margin: 5px 0 0 0;
        }
        </style>
        <div class="lcars-header">
            <div class="lcars-title">🖖 LCARS COMPUTER</div>
            <div class="lcars-subtitle">Interactive Installation System</div>
        </div>
    """, unsafe_allow_html=True)

def info_tooltip(text: str):
    """Render an info icon with tooltip."""
    st.markdown(f"""
        <span style="color: #9999FF; cursor: help;" title="{text}">ℹ️</span>
    """, unsafe_allow_html=True)

def command_box(command: str, description: str = "", language: str = "bash"):
    """Render a command box with copy functionality."""
    if description:
        st.caption(description)
    st.code(command, language=language)

def status_indicator(status: str, message: str):
    """Render a status indicator."""
    icons = {
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️",
        "pending": "⏳"
    }
    icon = icons.get(status, "•")
    st.markdown(f"{icon} {message}")

def render_cli_log():
    """Render the persistent CLI log at the bottom of the page."""
    if 'cli_log' not in st.session_state or not st.session_state.cli_log:
        return

    with st.expander("📟 Installation Log (CLI)", expanded=False):
        log_container = st.container()

        with log_container:
            # Show last 100 entries
            recent_logs = st.session_state.cli_log[-100:]

            log_text = ""
            for entry in recent_logs:
                level_color = {
                    'INFO': '#9999FF',
                    'WARNING': '#FFAA33',
                    'ERROR': '#FF6666',
                    'COMMAND_OUTPUT': '#66FF66'
                }.get(entry['level'], '#CCCCCC')

                log_text += f"<span style='color: #888888;'>[{entry['timestamp']}]</span> "
                log_text += f"<span style='color: {level_color};'>[{entry['level']}]</span> "
                log_text += f"<span style='color: #CCCCCC;'>{entry['message']}</span><br/>"

            st.markdown(f"""
                <div style="background-color: #0a0a0a;
                            padding: 15px;
                            border-radius: 5px;
                            border-left: 4px solid #FF9900;
                            font-family: 'Courier New', monospace;
                            font-size: 0.85em;
                            max-height: 400px;
                            overflow-y: auto;">
                    {log_text}
                </div>
            """, unsafe_allow_html=True)

            if st.button("🗑️ Clear Log"):
                st.session_state.cli_log = []
                st.rerun()

# =============================================================================
# STREAMLIT PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="LCARS Computer Installation",
    page_icon="🖖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for LCARS styling
st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background-color: #000000;
        color: #FF9900;
    }

    /* Headers */
    h1, h2, h3, h4 {
        color: #CC99CC !important;
        font-family: 'Arial', sans-serif;
    }

    /* Buttons */
    .stButton>button {
        background-color: #FF9900;
        color: black;
        border-radius: 15px;
        border: none;
        font-weight: bold;
        padding: 10px 25px;
        transition: all 0.3s;
    }

    .stButton>button:hover {
        background-color: #FFAA33;
        transform: scale(1.05);
    }

    /* Success boxes */
    .stSuccess {
        background-color: #112211;
        color: #66FF66;
        border-left: 4px solid #66FF66;
    }

    /* Info boxes */
    .stInfo {
        background-color: #111122;
        color: #9999FF;
        border-left: 4px solid #9999FF;
    }

    /* Warning boxes */
    .stWarning {
        background-color: #221111;
        color: #FFAA33;
        border-left: 4px solid #FFAA33;
    }

    /* Error boxes */
    .stError {
        background-color: #220000;
        color: #FF6666;
        border-left: 4px solid #FF6666;
    }

    /* Code blocks */
    .stCodeBlock {
        background-color: #1a1a1a;
        border-left: 4px solid #FF9900;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #1a0033;
        color: #FF9900;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #330066;
        color: #FFAA33;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1a0033;
        color: #FF9900;
        border-radius: 10px;
    }

    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #66FF66;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
init_session_state()

# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================

render_header()

st.sidebar.title("🚀 Installation Phases")
st.sidebar.markdown("---")

# Create navigation with enhanced styling
selected_step = st.sidebar.radio(
    "Select Phase:",
    options=[f"{icon} {name}" for icon, name, _ in NAV_ITEMS],
    format_func=lambda x: x,
)

# Extract the step name
step_name = selected_step.split(" ", 1)[1]

st.sidebar.markdown("---")

# Display current log file location
with st.sidebar.expander("📋 Installation Log"):
    st.caption(f"**Log file:** `{INSTALL_LOG.name}`")
    st.caption(f"**Location:** `{LOG_DIR}`")
    if st.button("📄 View Log"):
        if INSTALL_LOG.exists():
            with open(INSTALL_LOG, "r") as f:
                st.text(f.read())

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Hover over ℹ️ icons for helpful tooltips throughout the guide.")

# =============================================================================
# MAIN CONTENT SECTIONS
# =============================================================================

# --- SECTION: WELCOME ---
if step_name == "Welcome":
    st.title("🖖 Welcome to the LCARS Computer Installation")
    st.markdown("### Transform Your Home into the USS Enterprise")

    log_message("User accessed Welcome section")

    st.markdown("""
    Greetings, Commander! You are about to deploy a **privacy-first, self-hosted voice assistant**
    that combines the power of:
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a0033 0%, #330066 100%);
                    padding: 20px; border-radius: 15px; border-left: 4px solid #FF9900;">
            <h3 style="color: #CC99CC; margin-top: 0;">🏠 The Body</h3>
            <p style="color: #FF9900;"><strong>Home Assistant</strong></p>
            <p style="color: #CCCCCC; font-size: 0.9em;">
                State machine that controls lights, locks, sensors, and all smart devices
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a0033 0%, #330066 100%);
                    padding: 20px; border-radius: 15px; border-left: 4px solid #FF9900;">
            <h3 style="color: #CC99CC; margin-top: 0;">🧠 The Mind</h3>
            <p style="color: #FF9900;"><strong>Open WebUI + Ollama</strong></p>
            <p style="color: #CCCCCC; font-size: 0.9em;">
                Local LLM with LCARS persona for natural language understanding
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a0033 0%, #330066 100%);
                    padding: 20px; border-radius: 15px; border-left: 4px solid #FF9900;">
            <h3 style="color: #CC99CC; margin-top: 0;">⚡ The Nervous System</h3>
            <p style="color: #FF9900;"><strong>n8n</strong></p>
            <p style="color: #CCCCCC; font-size: 0.9em;">
                Workflow orchestrator that connects the mind and body
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("🎯 What You'll Accomplish Today")

    accomplishments = [
        ("Deploy 9 interconnected Docker containers", "All services fully isolated and secure"),
        ("Configure a local LLM voice assistant", "100% privacy-preserving, no cloud dependencies"),
        ("Integrate Home Assistant with AI", "Natural language control of your entire home"),
        ("Set up Wyoming voice pipeline", "Wake word detection, STT, and TTS"),
    ]

    for task, detail in accomplishments:
        col_icon, col_text = st.columns([1, 20])
        with col_icon:
            st.markdown("✅")
        with col_text:
            st.markdown(f"**{task}**")
            st.caption(detail)

    st.markdown("---")

    st.warning("⚠️ **Time Commitment:** This installation takes 15-45 minutes depending on your internet speed and hardware. Prepare your favorite beverage (Earl Grey, hot?) and let's begin.")

    st.markdown("---")

    st.subheader("📋 Prerequisites Checklist")

    prereq1 = st.checkbox("I have read the README.md and understand the system architecture")
    prereq2 = st.checkbox("I have a computer with Linux, Windows, or macOS")
    prereq3 = st.checkbox("I have at least 16GB RAM and 50GB free disk space")
    prereq4 = st.checkbox("I am ready to commit 30-45 minutes to this installation")

    if all([prereq1, prereq2, prereq3, prereq4]):
        st.success("✅ All prerequisites confirmed. Proceed to **Pre-Flight Check** when ready.")
        log_message("User confirmed all prerequisites")

# --- SECTION: PRE-FLIGHT CHECK ---
elif step_name == "Pre-Flight Check":
    st.title("🔍 Pre-Flight Check")
    st.markdown("### Verify System Requirements")

    log_message("User accessed Pre-Flight Check section")

    st.info("This automated check verifies your system meets the requirements for running the LCARS Computer.")

    if st.button("🚀 Run System Diagnostics", type="primary"):
        log_message("Running system diagnostics")

        with st.spinner("Scanning system..."):
            # Check 1: Operating System
            st.subheader("💻 Operating System")
            os_name = platform.system()
            os_version = platform.version()
            st.write(f"**Detected:** {os_name} {os_version}")

            if os_name in ["Linux", "Windows", "Darwin"]:
                status_indicator("success", f"{os_name} is supported")
                log_message(f"OS check passed: {os_name}")
            else:
                status_indicator("warning", f"{os_name} may have compatibility issues")
                log_message(f"OS check warning: {os_name}", "WARNING")

            st.markdown("---")

            # Check 2: RAM
            st.subheader("🧮 Memory (RAM)")
            try:
                if os_name == "Linux":
                    with open('/proc/meminfo', 'r') as f:
                        for line in f:
                            if line.startswith('MemTotal:'):
                                mem_kb = int(line.split()[1])
                                mem_gb = mem_kb / (1024 * 1024)
                                st.write(f"**Detected:** {mem_gb:.1f} GB")

                                if mem_gb >= 16:
                                    status_indicator("success", "RAM is sufficient (16+ GB recommended)")
                                    log_message(f"RAM check passed: {mem_gb:.1f} GB")
                                else:
                                    status_indicator("warning", f"Only {mem_gb:.1f} GB available. Performance may be degraded.")
                                    log_message(f"RAM check warning: {mem_gb:.1f} GB", "WARNING")
                                break
                else:
                    st.info("💡 Manual check: Ensure you have at least 16GB RAM")
                    log_message("RAM check skipped (non-Linux platform)", "INFO")
            except Exception as e:
                st.warning(f"Could not auto-detect RAM: {e}")
                log_message(f"RAM check failed: {e}", "ERROR")

            st.markdown("---")

            # Check 3: Disk Space
            st.subheader("💾 Disk Space")
            try:
                import shutil
                total, used, free = shutil.disk_usage(str(PROJECT_ROOT))
                free_gb = free / (1024 ** 3)
                st.write(f"**Available:** {free_gb:.1f} GB")

                if free_gb >= 50:
                    status_indicator("success", "Sufficient disk space (50+ GB recommended)")
                    log_message(f"Disk space check passed: {free_gb:.1f} GB free")
                else:
                    status_indicator("warning", f"Only {free_gb:.1f} GB free. You may run out of space.")
                    log_message(f"Disk space warning: {free_gb:.1f} GB free", "WARNING")
            except Exception as e:
                st.warning(f"Could not check disk space: {e}")
                log_message(f"Disk space check failed: {e}", "ERROR")

            st.markdown("---")

            # Check 4: GPU (Optional)
            st.subheader("🎮 GPU Acceleration (Optional)")
            gpu_available = check_command_exists("nvidia-smi")

            if gpu_available:
                returncode, output = execute_command_with_output("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
                if returncode == 0:
                    st.write(f"**Detected:** {output.strip()}")
                    status_indicator("success", "NVIDIA GPU detected - inference will be fast!")
                    log_message(f"GPU detected: {output.strip()}")
                else:
                    status_indicator("info", "No NVIDIA GPU detected - CPU inference will be used (slower)")
                    log_message("No GPU detected")
            else:
                status_indicator("info", "No NVIDIA GPU detected - CPU inference will be used (slower)")
                log_message("nvidia-smi not found")

            st.markdown("---")

            # Check 5: Docker
            st.subheader("🐳 Docker")
            docker_installed = check_command_exists("docker")

            if docker_installed:
                returncode, output = execute_command_with_output("docker --version")
                if returncode == 0:
                    st.write(f"**Installed:** {output.strip()}")
                    status_indicator("success", "Docker is installed")
                    log_message(f"Docker found: {output.strip()}")
                else:
                    status_indicator("error", "Docker command failed")
                    log_message("Docker command failed", "ERROR")
            else:
                status_indicator("error", "Docker is NOT installed - proceed to Docker Setup")
                log_message("Docker not found", "ERROR")

        st.success("✅ Pre-flight check complete! Review the results above and proceed to the next step.")

# --- SECTION: DOCKER SETUP ---
elif step_name == "Docker Setup":
    st.title("🐳 Docker Setup")
    st.markdown("### Install Docker and Docker Compose")

    log_message("User accessed Docker Setup section")

    st.info("""
    Docker is the foundation of the LCARS Computer. All services run in isolated containers,
    making installation and management significantly easier.
    """)

    # Tabbed interface for different OS
    tab1, tab2, tab3 = st.tabs(["🐧 Linux", "🪟 Windows", "🍎 macOS"])

    with tab1:
        st.subheader("Linux Installation (Recommended)")

        st.markdown("""
        For **Ubuntu**, **Debian**, or **Linux Mint**, use Docker's official installation script:
        """)

        with st.expander("📋 View Installation Commands"):
            command_box("""# Update system packages
sudo apt update

# Download Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh

# Run the installation script
sudo sh get-docker.sh

# Add your user to the docker group (avoid needing sudo)
sudo usermod -aG docker $USER

# Clean up
rm get-docker.sh""", description="Copy and paste these commands into your terminal")

        st.warning("⚠️ **Important:** After running these commands, log out and log back in for the group changes to take effect!")

        if st.button("✅ I have completed the Linux installation"):
            st.success("Excellent! Verify by running `docker --version` in your terminal.")
            log_message("User completed Linux Docker installation")

    with tab2:
        st.subheader("Windows Installation")

        st.markdown("""
        1. **Download Docker Desktop for Windows**
           - Visit: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

        2. **Run the installer**
           - Ensure **WSL 2** is selected during installation
           - This provides better performance than Hyper-V

        3. **Start Docker Desktop**
           - Launch from Start Menu
           - Wait for the engine to fully start (whale icon in system tray)

        4. **Verify Installation**
           - Open PowerShell or Command Prompt
           - Run: `docker --version`
        """)

        st.info("💡 **Note:** On Windows, you'll use `docker-compose.desktop.yml` instead of the standard compose file due to networking differences.")

        if st.button("✅ I have installed Docker Desktop on Windows"):
            st.success("Great! Make sure Docker Desktop is running before proceeding.")
            log_message("User completed Windows Docker installation")

    with tab3:
        st.subheader("macOS Installation")

        st.markdown("""
        1. **Download Docker Desktop for Mac**
           - Visit: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
           - Choose the correct version for your chip (Intel or Apple Silicon)

        2. **Install the application**
           - Drag Docker to Applications folder
           - Launch Docker Desktop

        3. **Wait for startup**
           - Docker Desktop will prompt for permissions
           - Wait for the engine to fully start

        4. **Verify Installation**
           - Open Terminal
           - Run: `docker --version`
        """)

        st.info("💡 **Note:** On macOS, you'll use `docker-compose.desktop.yml` instead of the standard compose file due to networking differences.")

        if st.button("✅ I have installed Docker Desktop on macOS"):
            st.success("Perfect! Ensure Docker Desktop is running before moving forward.")
            log_message("User completed macOS Docker installation")

    st.markdown("---")

    st.subheader("🧪 Verification")

    if st.button("🔍 Test Docker Installation"):
        with st.spinner("Testing Docker..."):
            log_message("Testing Docker installation")

            # Test docker command
            docker_works = check_command_exists("docker")
            if docker_works:
                returncode, output = execute_command_with_output("docker --version")
                st.code(output, language="text")
                if returncode == 0:
                    status_indicator("success", "Docker is installed and working!")
                    log_message("Docker test passed")
                else:
                    status_indicator("error", "Docker command failed")
                    log_message("Docker test failed", "ERROR")
            else:
                status_indicator("error", "Docker command not found")
                log_message("Docker not found", "ERROR")

            # Test docker compose
            returncode, output = execute_command_with_output("docker compose version")
            st.code(output, language="text")
            if returncode == 0:
                status_indicator("success", "Docker Compose is available!")
                log_message("Docker Compose test passed")
            else:
                status_indicator("error", "Docker Compose not found")
                log_message("Docker Compose test failed", "ERROR")

# --- SECTION: CONFIGURATION ---
elif step_name == "Configuration":
    st.title("⚙️ Configuration")
    st.markdown("### Generate Secure Environment Variables")

    log_message("User accessed Configuration section")

    st.info("""
    The LCARS Computer requires several environment variables for security and configuration.
    This step will generate a `.env` file with secure, random credentials.
    """)

    st.warning("⚠️ **Security Notice:** The generated `.env` file contains secrets and should NEVER be committed to version control.")

    # Check if .env already exists
    env_file = DOCKER_DIR / ".env"
    env_exists = env_file.exists()

    if env_exists:
        st.warning(f"⚠️ An `.env` file already exists at `{env_file}`")
        st.info("You can regenerate it (this will backup the existing file) or skip this step.")

    st.markdown("---")

    st.subheader("📝 Environment Variables to Generate")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        - **POSTGRES_PASSWORD**: Database password for n8n
        - **N8N_ENCRYPTION_KEY**: Encrypts n8n credentials (⚠️ changing this breaks stored credentials)
        - **WEBUI_SECRET_KEY**: Session encryption for Open WebUI
        """)

    with col2:
        st.markdown("""
        - **TIMEZONE**: Your local timezone
        - **HA_ACCESS_TOKEN**: Home Assistant token (added manually later)
        - **WHISPER_MODEL**: Speech-to-text model selection
        """)

    st.markdown("---")

    # Timezone selection
    st.subheader("🌍 Select Your Timezone")
    timezone = st.selectbox(
        "Choose your timezone:",
        [
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "America/Phoenix",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Australia/Sydney",
        ]
    )

    st.session_state.environment_vars['TIMEZONE'] = timezone

    st.markdown("---")

    # Generate button
    if st.button("🔐 Generate Secure .env File", type="primary"):
        with st.spinner("Generating secure credentials..."):
            log_message("Generating .env file")

            # Backup existing file
            if env_exists:
                backup_path = DOCKER_DIR / f".env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                env_file.rename(backup_path)
                st.info(f"📦 Existing file backed up to: `{backup_path.name}`")
                log_message(f"Backed up existing .env to {backup_path}")

            # Generate secrets
            n8n_key = generate_secure_secret(32)
            postgres_pw = generate_secure_password(24)
            webui_key = generate_secure_secret(32)

            # Create .env content
            env_content = f"""# LCARS Computer - Environment Configuration
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# ⚠️ SECURITY WARNING: This file contains secrets. Never commit to version control.

# ==========================================================================
# GENERAL SETTINGS
# ==========================================================================
TIMEZONE={timezone}

# ==========================================================================
# N8N CONFIGURATION
# ==========================================================================
N8N_HOST=localhost
WEBHOOK_URL=http://localhost:5678/
N8N_ENCRYPTION_KEY={n8n_key}

# ==========================================================================
# DATABASE CONFIGURATION
# ==========================================================================
POSTGRES_PASSWORD={postgres_pw}

# ==========================================================================
# OPEN WEBUI CONFIGURATION
# ==========================================================================
WEBUI_SECRET_KEY={webui_key}

# ==========================================================================
# HOME ASSISTANT CONFIGURATION
# ==========================================================================
# TODO: Add your Long-Lived Access Token after Home Assistant is running
# Get it from: http://localhost:8123/profile/security
HA_ACCESS_TOKEN=PASTE_YOUR_TOKEN_HERE
HA_URL=http://host.docker.internal:8123

# ==========================================================================
# VOICE PIPELINE SETTINGS
# ==========================================================================
WHISPER_MODEL=medium-int8
PIPER_VOICE=en_US-amy-medium

# Wake word model (openWakeWord / Wyoming)
# Default matches docker-compose.yml. If you add a custom wake word model named
# "computer" into docker/volumes/openwakeword/, set this to "computer".
OPENWAKEWORD_PRELOAD_MODEL=ok_nabu

# ==========================================================================
# GPU CONFIGURATION (uncomment if NVIDIA GPU available)
# ==========================================================================
# NVIDIA_VISIBLE_DEVICES=all
# NVIDIA_DRIVER_CAPABILITIES=compute,utility
"""

            # Write file
            env_file.write_text(env_content, encoding='utf-8')

            st.success(f"✅ Successfully generated `.env` file at `{env_file}`")
            log_message("Successfully generated .env file")

            # Show preview (with secrets masked)
            with st.expander("👁️ Preview Generated File (secrets masked)"):
                masked_content = env_content.replace(n8n_key, "***MASKED***")
                masked_content = masked_content.replace(postgres_pw, "***MASKED***")
                masked_content = masked_content.replace(webui_key, "***MASKED***")
                st.code(masked_content, language="bash")

            st.info("""
            📌 **Next Steps:**
            1. Proceed to **Deployment** to start the Docker stack
            2. After Home Assistant is running, you'll add the access token to this file
            """)

# --- SECTION: DEPLOYMENT ---
elif step_name == "Deployment":
    st.title("🚀 Deployment")
    st.markdown("### Deploy the Docker Stack")

    log_message("User accessed Deployment section")

    st.info("""
    This step will deploy the LCARS Computer system. You can use a standard deployment (all defaults)
    or customize ports and use existing infrastructure.
    """)

    # Check if .env exists
    env_file = DOCKER_DIR / ".env"
    if not env_file.exists():
        st.error("❌ No `.env` file found! Please complete the **Configuration** step first.")
        st.stop()

    # Import deployment configuration module
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        import deploy_config
    except ImportError:
        st.error("❌ Could not import deploy_config module")
        st.stop()

    # Platform detection
    current_os = platform.system()

    # Deployment Mode Selection (only show if not selected)
    if st.session_state.deployment_mode is None:
        st.subheader("🎯 Select Deployment Mode")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #1a0033 0%, #330066 100%);
                        padding: 20px; border-radius: 15px; border-left: 4px solid #66FF66; height: 250px;">
                <h3 style="color: #66FF66; margin-top: 0;">⚡ Standard Deployment</h3>
                <p style="color: #CCCCCC; font-size: 0.9em;">
                    <strong>Best for:</strong> New installations<br/>
                    <strong>Features:</strong><br/>
                    • All services deployed fresh<br/>
                    • Default ports used<br/>
                    • Fastest setup time<br/>
                    • No manual configuration needed
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚀 Use Standard Deployment", key="standard_deploy", type="primary"):
                st.session_state.deployment_mode = "standard"
                st.session_state.deployment_config = copy.deepcopy(deploy_config.DEFAULT_SERVICES)
                log_message("User selected standard deployment mode")
                st.rerun()

        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #1a0033 0%, #330066 100%);
                        padding: 20px; border-radius: 15px; border-left: 4px solid #FF9900; height: 250px;">
                <h3 style="color: #FF9900; margin-top: 0;">🔧 Custom Deployment</h3>
                <p style="color: #CCCCCC; font-size: 0.9em;">
                    <strong>Best for:</strong> Advanced users<br/>
                    <strong>Features:</strong><br/>
                    • Use existing infrastructure<br/>
                    • Custom port configuration<br/>
                    • Service-by-service control<br/>
                    • Infrastructure detection
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("⚙️ Use Custom Deployment", key="custom_deploy"):
                st.session_state.deployment_mode = "custom"
                # Initialize with default config that user can modify
                st.session_state.deployment_config = copy.deepcopy(deploy_config.DEFAULT_SERVICES)
                log_message("User selected custom deployment mode")
                st.rerun()

        st.stop()  # Don't show anything else until mode is selected

    # Show current mode
    mode_display = "⚡ Standard" if st.session_state.deployment_mode == "standard" else "🔧 Custom"
    st.info(f"**Deployment Mode:** {mode_display}")

    if st.button("🔄 Change Deployment Mode"):
        st.session_state.deployment_mode = None
        st.session_state.deployment_config = None
        log_message("User reset deployment mode")
        st.rerun()

    st.markdown("---")

    # CUSTOM DEPLOYMENT CONFIGURATION
    if st.session_state.deployment_mode == "custom":
        st.subheader("🔍 Infrastructure Discovery")

        col_scan, col_manual = st.columns(2)

        with col_scan:
            if st.button("🔎 Auto-Detect Services", type="secondary"):
                with st.spinner("Scanning system for existing services..."):
                    log_message("Scanning for existing services")

                    # Detect existing services
                    detected_services = deploy_config.detect_existing_services()

                    # Merge with existing config to preserve user changes
                    if st.session_state.deployment_config:
                        for key, detected_svc in detected_services.items():
                            if key in st.session_state.deployment_config:
                                # Update detection info but preserve user settings
                                st.session_state.deployment_config[key].detected_host = detected_svc.detected_host
                                st.session_state.deployment_config[key].detected_port = detected_svc.detected_port
                    else:
                        st.session_state.deployment_config = detected_services

                    # Check Docker containers
                    containers = deploy_config.check_docker_containers()

                    # Cache discovery summary so results persist across reruns
                    st.session_state.deployment_last_discovery = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "detected_services": {
                            k: {
                                "name": v.name,
                                "detected_host": v.detected_host,
                                "detected_port": v.detected_port,
                                "connection_string": v.connection_string,
                            }
                            for k, v in detected_services.items()
                            if v.detected_port
                        },
                        "containers": containers,
                    }

                    st.success("✅ Scan complete!")
                    log_message("Infrastructure scan completed")

                    # Show detected services
                    found_count = sum(1 for svc in detected_services.values() if svc.detected_port)

                    if found_count > 0:
                        st.info(f"Found {found_count} potentially usable services")
                        for key, service in detected_services.items():
                            if service.detected_port:
                                st.caption(f"✅ **{service.name}** at `{service.connection_string}`")
                    else:
                        st.warning("No existing services detected.")

                    if containers:
                        st.caption("**Existing Docker Containers:**")
                        for name, info in containers.items():
                            st.caption(f"• {name}: {info['status']}")

            # Persisted discovery summary (shown even when button not pressed)
            last_discovery = st.session_state.deployment_last_discovery
            if last_discovery:
                with st.expander(f"📌 Last scan results ({last_discovery['timestamp']})", expanded=False):
                    detected_services_summary = last_discovery.get("detected_services") or {}
                    if detected_services_summary:
                        st.markdown("**Detected services:**")
                        for svc in detected_services_summary.values():
                            st.caption(f"✅ **{svc['name']}** at `{svc['connection_string']}`")
                    else:
                        st.caption("No services detected in last scan.")

                    containers_summary = last_discovery.get("containers") or {}
                    if containers_summary:
                        st.markdown("**Existing Docker containers:**")
                        for name, info in containers_summary.items():
                            status = info.get("status", "unknown")
                            st.caption(f"• {name}: {status}")

        with col_manual:
            st.info("💡 **Manual Configuration**: Services can be configured below without scanning")

        st.markdown("---")

        # Service Configuration
        if st.session_state.deployment_config:
            st.subheader("⚙️ Service Configuration")

            services_config = st.session_state.deployment_config

            # Quick Setup Presets
            st.markdown("### 🎯 Quick Setup Presets")

            preset_col1, preset_col2 = st.columns([3, 1])

            with preset_col1:
                preset = st.selectbox(
                    "Choose a configuration preset:",
                    [
                        "🔧 Full Custom (manual configuration)",
                        "⚡ Minimal Install (all services new)",
                        "💾 Reuse Database Only (existing PostgreSQL)",
                        "🤖 Reuse LLM Server (existing Ollama)",
                        "🌐 Reuse All Infrastructure",
                    ],
                    help="Quick presets to configure common deployment scenarios"
                )

            with preset_col2:
                if st.button("Apply Preset"):
                    if "Minimal Install" in preset:
                        # All services deploy new
                        for svc in services_config.values():
                            svc.use_existing = False
                        st.success("✅ Preset applied: All services will deploy new")
                        log_message("Applied Minimal Install preset")

                    elif "Reuse Database Only" in preset:
                        # Only PostgreSQL uses existing
                        for key, svc in services_config.items():
                            svc.use_existing = (key == "postgres")
                        st.success("✅ Preset applied: Connect to existing PostgreSQL, deploy others new")
                        log_message("Applied Reuse Database preset")

                    elif "Reuse LLM Server" in preset:
                        # Only Ollama uses existing
                        for key, svc in services_config.items():
                            svc.use_existing = (key == "ollama")
                        st.success("✅ Preset applied: Connect to existing Ollama, deploy others new")
                        log_message("Applied Reuse LLM Server preset")

                    elif "Reuse All Infrastructure" in preset:
                        # All services that can use existing will
                        for svc in services_config.values():
                            if svc.can_use_existing:
                                svc.use_existing = True
                        st.success("✅ Preset applied: Connect to all existing services detected")
                        log_message("Applied Reuse All Infrastructure preset")

            st.markdown("---")

            # Proactive Networking Guidance
            st.info("""
💡 **Networking Quick Guide:**
- **Existing service on this machine:** Use `host.docker.internal` (not `localhost`)
- **Remote server:** Use hostname or IP address (e.g., `db.example.com`, `192.168.1.100`)
- **Cloud/managed service:** Use provided endpoint (e.g., `mydb.us-east-1.rds.amazonaws.com`)
- **Another Docker container:** Use container name (e.g., `postgres`, `ollama`)
""")

            st.markdown("---")

            # Progress Indicator
            configured_services = [
                svc for svc in services_config.values()
                if svc.use_existing and (svc.custom_host or svc.detected_host)
            ]
            total_services = len(services_config)
            configured_count = len(configured_services)

            progress_col1, progress_col2 = st.columns([3, 1])
            with progress_col1:
                st.markdown("#### 📊 Configuration Progress")
            with progress_col2:
                st.caption(f"{configured_count}/{total_services} services customized")

            if configured_count > 0:
                st.progress(configured_count / total_services)

            st.markdown("---")

            # Service Categories
            CRITICAL_SERVICES = ["homeassistant", "postgres", "n8n"]
            OPTIONAL_SERVICES = ["redis", "ollama", "open-webui"]
            VOICE_SERVICES = ["whisper", "piper", "openwakeword"]

            # First pass: Checkboxes OUTSIDE form so they update immediately
            st.markdown("### Select Services to Connect")

            # Critical Services
            with st.expander("🔴 **Critical Services** (Required for core functionality)", expanded=True):
                st.markdown("These services are required for LCARS Computer to function.")
                for key, service in services_config.items():
                    if key in CRITICAL_SERVICES and service.can_use_existing:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            # Show configuration summary
                            config_summary = ""
                            if service.use_existing:
                                if service.custom_host or service.detected_host:
                                    host = service.custom_host or service.detected_host or service.default_host
                                    port = service.custom_port or service.detected_port or service.default_port
                                    config_summary = f" → `{host}:{port}`"
                                else:
                                    config_summary = " → *needs configuration*"
                            else:
                                config_summary = " → Deploy new"

                            use_existing = st.checkbox(
                                f"🔌 Connect to existing/remote **{service.name}**{config_summary}",
                                value=service.use_existing,
                                key=f"use_existing_{key}",
                                help=f"Check this to connect to an existing {service.name} instance (local, remote, or 3rd-party). Uncheck to deploy a new container.",
                            )
                            service.use_existing = use_existing
                        with col2:
                            if service.detected_port:
                                status_indicator("success", f"Found:{service.detected_port}")
                            else:
                                status_indicator("info", "Not found")

            # Optional Services
            with st.expander("🟡 **Optional Services** (Recommended but not required)", expanded=True):
                st.markdown("These services enhance functionality but are not strictly required.")
                for key, service in services_config.items():
                    if key in OPTIONAL_SERVICES and service.can_use_existing:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            # Show configuration summary
                            config_summary = ""
                            if service.use_existing:
                                if service.custom_host or service.detected_host:
                                    host = service.custom_host or service.detected_host or service.default_host
                                    port = service.custom_port or service.detected_port or service.default_port
                                    config_summary = f" → `{host}:{port}`"
                                else:
                                    config_summary = " → *needs configuration*"
                            else:
                                config_summary = " → Deploy new"

                            use_existing = st.checkbox(
                                f"🔌 Connect to existing/remote **{service.name}**{config_summary}",
                                value=service.use_existing,
                                key=f"use_existing_{key}",
                                help=f"Check this to connect to an existing {service.name} instance (local, remote, or 3rd-party). Uncheck to deploy a new container.",
                            )
                            service.use_existing = use_existing
                        with col2:
                            if service.detected_port:
                                status_indicator("success", f"Found:{service.detected_port}")
                            else:
                                status_indicator("info", "Not found")

            # Voice Services
            with st.expander("🎤 **Voice Services** (Only needed for voice satellites)", expanded=False):
                st.markdown("Only required if you plan to use voice satellites with wake word detection.")
                for key, service in services_config.items():
                    if key in VOICE_SERVICES and service.can_use_existing:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            # Show configuration summary
                            config_summary = ""
                            if service.use_existing:
                                if service.custom_host or service.detected_host:
                                    host = service.custom_host or service.detected_host or service.default_host
                                    port = service.custom_port or service.detected_port or service.default_port
                                    config_summary = f" → `{host}:{port}`"
                                else:
                                    config_summary = " → *needs configuration*"
                            else:
                                config_summary = " → Deploy new"

                            use_existing = st.checkbox(
                                f"🔌 Connect to existing/remote **{service.name}**{config_summary}",
                                value=service.use_existing,
                                key=f"use_existing_{key}",
                                help=f"Check this to connect to an existing {service.name} instance (local, remote, or 3rd-party). Uncheck to deploy a new container.",
                            )
                            service.use_existing = use_existing
                        with col2:
                            if service.detected_port:
                                status_indicator("success", f"Found:{service.detected_port}")
                            else:
                                status_indicator("info", "Not found")

            st.markdown("---")
            st.markdown("#### Configure Connection Details")

            # Second pass: Configuration form (now checkboxes are already set)
            with st.form("custom_deployment_service_config_form"):
                for key, service in services_config.items():
                    with st.expander(f"🔧 {service.name} - {service.description}"):
                        if not service.can_use_existing:
                            st.info(f"ℹ️ {service.name} must be deployed fresh (requires specific LCARS configuration)")

                        # Always show connection fields for services that can use existing infrastructure
                        if service.can_use_existing:
                            if service.use_existing:
                                st.markdown("**🌐 Remote/Existing Server Connection:**")
                            else:
                                st.markdown("**🐳 New Container Deployment:**")

                            col_host, col_port = st.columns(2)

                            with col_host:
                                # Allow the user to specify the host the installer should use for
                                # access + health checks, even when deploying new containers.
                                # (Example: running the installer on a different machine than the stack.)
                                default_host = service.custom_host or service.detected_host or service.default_host
                                host_label = "Hostname/IP Address:" if service.use_existing else "Host (for access/health checks):"
                                host_help = (
                                    "Hostname or IP address where this service is reachable from this installer "
                                    "(e.g., 'localhost', 'server.lan', '192.168.1.100')."
                                )
                                if not service.use_existing:
                                    host_help += f" This service will be deployed as a container named '{key}'."

                                custom_host = st.text_input(
                                    host_label,
                                    value=default_host,
                                    placeholder=service.default_host,
                                    key=f"host_{key}",
                                    help=host_help,
                                )
                                service.custom_host = custom_host

                                # Reminder: from inside containers, localhost is the container itself.
                                # This warning only applies when reusing an existing host-side service.
                                if service.use_existing and custom_host in ["localhost", "127.0.0.1", "::1"]:
                                    st.warning(
                                        "⚠️ If other containers must reach this host-side service, use `host.docker.internal` "
                                        "for container-to-host access (not `localhost`)."
                                    )

                                # Validate hostname
                                is_valid, error = deploy_config.validate_hostname(custom_host)
                                if not is_valid:
                                    st.error(f"❌ {error}")

                            with col_port:
                                if service.use_existing:
                                    # Use custom_port if set, otherwise detected, otherwise default
                                    default_port = service.custom_port or service.detected_port or service.default_port
                                    custom_port = st.number_input(
                                        "Port:",
                                        value=default_port,
                                        min_value=1,
                                        max_value=65535,
                                        key=f"port_{key}",
                                        help=f"Port number on the remote/existing server (default: {service.default_port})",
                                    )
                                    service.custom_port = int(custom_port)
                                else:
                                    # Deploy new container - allow external port customization
                                    default_deploy_port = service.custom_port or service.default_port
                                    deploy_port = st.number_input(
                                        "External Port:",
                                        value=default_deploy_port,
                                        min_value=1,
                                        max_value=65535,
                                        key=f"deploy_port_{key}",
                                        help=f"Port to expose on host machine (default: {service.default_port})",
                                    )
                                    service.custom_port = int(deploy_port)

                                    if deploy_port != service.default_port:
                                        st.info(
                                            f"ℹ️ Host port {deploy_port} → Container port {service.default_port}"
                                        )

                            # Health check and test connection (only for existing services)
                            if service.use_existing:
                                # Show last health-check result (if any)
                                health = st.session_state.deployment_service_health.get(key)
                                if health is not None:
                                    if health.get("ok"):
                                        st.success(f"✅ {service.name} is responding!")
                                    else:
                                        st.error(f"❌ Connection failed: {health.get('error')}")
                                        use_anyway = st.checkbox(
                                            "Use this service anyway (infrastructure may not be ready yet)",
                                            key=f"force_{key}",
                                        )
                                        if use_anyway:
                                            st.warning("⚠️ Service will be used despite health check failure")

                                test_clicked = st.form_submit_button("🩺 Test Connection", key=f"test_{key}")
                                if test_clicked:
                                    with st.spinner(f"Testing {service.name}..."):
                                        is_healthy, error_msg = deploy_config.check_service_health(service)
                                        st.session_state.deployment_service_health[key] = {
                                            "ok": bool(is_healthy),
                                            "error": error_msg,
                                        }
                                        if is_healthy:
                                            log_message(f"Health check passed for {service.name} at {service.connection_string}")
                                        else:
                                            log_message(f"Health check failed for {service.name}: {error_msg}", "ERROR")
                        else:
                            # Service cannot use existing - only show port configuration
                            st.markdown("**🐳 New Container Deployment:**")

                            col_host, col_port = st.columns(2)

                            with col_host:
                                default_host = service.custom_host or service.default_host
                                custom_host = st.text_input(
                                    "Host (for access/health checks):",
                                    value=default_host,
                                    placeholder=service.default_host,
                                    key=f"host_{key}",
                                    help=(
                                        "Hostname or IP address where this service will be reachable from this installer "
                                        "(usually 'localhost' when deploying locally). "
                                        f"This service will be deployed as a container named '{key}'."
                                    ),
                                )
                                service.custom_host = custom_host

                                is_valid, error = deploy_config.validate_hostname(custom_host)
                                if not is_valid:
                                    st.error(f"❌ {error}")

                            with col_port:
                                default_deploy_port = service.custom_port or service.default_port
                                deploy_port = st.number_input(
                                    "External Port:",
                                    value=default_deploy_port,
                                    min_value=1,
                                    max_value=65535,
                                    key=f"deploy_port_required_{key}",
                                    help=f"Port to expose on host machine (default: {service.default_port})",
                                )
                                service.custom_port = int(deploy_port)

                                if deploy_port != service.default_port:
                                    st.info(
                                        f"ℹ️ Host port {deploy_port} → Container port {service.default_port}"
                                    )

                st.markdown("---")

                save_clicked = st.form_submit_button("💾 Save Configuration & Continue", type="primary")

            if save_clicked:
                # Validate configuration
                errors = []

                for key, service in services_config.items():
                    if service.required and service.use_existing:
                        is_healthy, error_msg = deploy_config.check_service_health(service)
                        if not is_healthy and f"force_{key}" not in st.session_state:
                            errors.append(f"{service.name}: {error_msg}")

                if errors:
                    st.error("❌ Configuration errors detected:")
                    for error in errors:
                        st.markdown(f"• {error}")
                else:
                    # Save configuration
                    config_path = DOCKER_DIR / "deployment_config.json"
                    deploy_config.save_deployment_config(services_config, config_path)

                    # Write docker-compose override (auto-applied by `docker compose up` on Linux)
                    override_path = DOCKER_DIR / "docker-compose.override.yml"
                    override_content = deploy_config.generate_docker_compose_override(services_config)
                    override_path.write_text(override_content, encoding="utf-8")

                    # Update docker/.env so containers use the selected endpoints
                    env_path = DOCKER_DIR / ".env"

                    ha_service = services_config.get("homeassistant")
                    if ha_service and ha_service.use_existing:
                        upsert_env_var(
                            env_path,
                            "HA_URL",
                            f"http://{ha_service.effective_host}:{ha_service.effective_port}",
                        )

                    ollama_service = services_config.get("ollama")
                    if ollama_service and ollama_service.use_existing:
                        upsert_env_var(
                            env_path,
                            "OLLAMA_BASE_URL",
                            f"http://{ollama_service.effective_host}:{ollama_service.effective_port}",
                        )
                    else:
                        # Default for in-stack Open WebUI -> Ollama
                        upsert_env_var(env_path, "OLLAMA_BASE_URL", "http://ollama:11434")

                    postgres_service = services_config.get("postgres")
                    if postgres_service and postgres_service.use_existing:
                        upsert_env_var(env_path, "DB_POSTGRESDB_HOST", postgres_service.effective_host)
                        upsert_env_var(env_path, "DB_POSTGRESDB_PORT", str(postgres_service.effective_port))
                    else:
                        upsert_env_var(env_path, "DB_POSTGRESDB_HOST", "postgres")
                        upsert_env_var(env_path, "DB_POSTGRESDB_PORT", "5432")

                    st.success("✅ Configuration saved successfully!")
                    log_message("Deployment configuration saved")

                    # Show summary
                    st.subheader("📋 Deployment Summary")

                    existing_services = [svc.name for svc in services_config.values() if svc.use_existing]
                    new_services = [svc.name for svc in services_config.values() if not svc.use_existing]

                    if existing_services:
                        st.markdown("**Using Existing:**")
                        for name in existing_services:
                            st.markdown(f"• {name}")

                    if new_services:
                        st.markdown("**Deploying New:**")
                        for name in new_services:
                            st.markdown(f"• {name}")

                    st.info("📌 Proceed to execute deployment below")

    # DEPLOYMENT EXECUTION
    if st.session_state.deployment_mode and (st.session_state.deployment_mode == "standard" or
                                              (st.session_state.deployment_config is not None and
                                               (DOCKER_DIR / "deployment_config.json").exists())):

        st.subheader("📦 Execute Deployment")

        if current_os == "Linux":
            st.markdown("**Detected Platform:** Linux (recommended)")

            tab1, tab2 = st.tabs(["🤖 Automated Deployment", "🔧 Manual Deployment"])

            with tab1:
                st.markdown("### Automated Deployment Script")
                st.markdown("The `deploy.sh` script handles everything automatically:")

                gpu_mode = st.checkbox("🎮 Enable NVIDIA GPU acceleration (if available)")

                if gpu_mode:
                    deploy_command = "bash ./scripts/deploy.sh --gpu"
                    deploy_args = ["bash", "./scripts/deploy.sh", "--gpu"]
                else:
                    deploy_command = "bash ./scripts/deploy.sh"
                    deploy_args = ["bash", "./scripts/deploy.sh"]

                command_box(deploy_command, "Run this command from the project root:")

                if st.button("🚀 Execute Automated Deployment", type="primary"):
                    with st.spinner("Deploying LCARS Computer stack..."):
                        log_message(f"Running automated deployment: {deploy_command}")

                        output_container = st.empty()
                        returncode, output = execute_command_with_output(deploy_args, cwd=PROJECT_ROOT)

                        output_container.code(output, language="text")

                        if returncode == 0:
                            st.success("✅ Deployment completed successfully!")
                            log_message("Automated deployment completed successfully")
                            st.balloons()
                        else:
                            st.error(f"❌ Deployment failed with return code {returncode}")
                            log_message(f"Deployment failed with code {returncode}", "ERROR")

            with tab2:
                st.markdown("### Manual Deployment")

                with st.expander("📋 Step 1: Create Docker network"):
                    command_box("docker network create lcars_network", "Create the dedicated network:")
                    if st.button("▶️ Run: Create network"):
                        returncode, output = execute_command_with_output("docker network create lcars_network")
                        st.code(output, language="text")
                        if returncode == 0:
                            st.success("✅ Network created")
                            log_message("Docker network created")

                with st.expander("📋 Step 2: Start containers"):
                    command_box("""cd docker
docker compose up -d""", "Navigate to docker/ and start services:")
                    if st.button("▶️ Run: Start containers"):
                        returncode, output = execute_command_with_output("docker compose up -d", cwd=DOCKER_DIR)
                        st.code(output, language="text")
                        if returncode == 0:
                            st.success("✅ Containers started")
                            log_message("Docker containers started")

        else:
            # Windows/macOS
            st.markdown(f"**Detected Platform:** {current_os}")
            st.warning("⚠️ You must use the `docker-compose.desktop.yml` file on Windows/macOS due to networking differences.")

            with st.expander("📋 Step 1: Generate environment file (if not done)"):
                command_box("python scripts/setup.py --generate-env", "Ensure .env file exists:")

            with st.expander("📋 Step 2: Start the stack"):
                desktop_command = "docker compose -f docker-compose.desktop.yml up -d"
                command_box(desktop_command, "Navigate to docker/ directory first:")

                if st.button("🚀 Execute Desktop Deployment", type="primary"):
                    with st.spinner("Starting Docker containers..."):
                        log_message("Running desktop deployment")

                        output_container = st.empty()
                        returncode, output = execute_command_with_output(desktop_command, cwd=DOCKER_DIR)

                        output_container.code(output, language="text")

                        if returncode == 0:
                            st.success("✅ Containers started successfully!")
                            log_message("Desktop deployment successful")
                            st.balloons()
                        else:
                            st.error(f"❌ Deployment failed with return code {returncode}")
                            log_message(f"Desktop deployment failed: {returncode}", "ERROR")

        st.markdown("---")

        st.subheader("📊 Container Status")

        if st.button("🔍 Check Container Status"):
            with st.spinner("Checking running containers..."):
                returncode, output = execute_command_with_output("docker compose ps", cwd=DOCKER_DIR)
                st.code(output, language="text")

                if returncode == 0:
                    st.success("✅ Container status retrieved")
                    log_message("Container status checked")
                else:
                    st.error("❌ Failed to get container status")
                    log_message("Failed to check container status", "ERROR")

# --- SECTION: INTEGRATION ---
elif step_name == "Integration":
    st.title("🔗 Integration - The Critical Phase")
    st.markdown("### Connect All Services to Create Your Voice-Controlled Home")

    log_message("User accessed Integration section")

    st.warning("""
    ⚠️ **This is the most important phase!** The containers are running, but they're not connected yet.
    Without these integrations, the LLM cannot control your home. Take your time with each step.

    **Estimated time:** 20-30 minutes
    """)

    st.markdown("---")

    # Progress tracking
    integration_steps = {
        "ha_setup": "Home Assistant Initial Setup",
        "ha_token": "Generate Access Token",
        "open_webui": "Configure Open WebUI & Pull Model",
        "lcars_persona": "Import LCARS Persona",
        "hacs": "Install HACS",
        "extended_openai": "Install Extended OpenAI Conversation",
        "extended_openai_config": "Configure Extended OpenAI with Tools",
        "n8n_workflows": "Import n8n Workflows",
        "assist_pipeline": "Configure Assist Pipeline",
    }

    # Initialize session state for integration progress
    if 'integration_progress' not in st.session_state:
        st.session_state.integration_progress = {key: False for key in integration_steps.keys()}

    # Progress indicator
    completed_steps = sum(st.session_state.integration_progress.values())
    total_steps = len(integration_steps)

    st.markdown(f"### 📊 Integration Progress: {completed_steps}/{total_steps} steps complete")
    if completed_steps > 0:
        st.progress(completed_steps / total_steps)

    st.markdown("---")

    # ==========================================================================
    # STEP 1: Home Assistant Initial Setup
    # ==========================================================================
    st.subheader("1️⃣ Home Assistant Initial Setup")

    st.markdown("""
    First, let's create your Home Assistant account and complete the onboarding:

    1. Open [http://localhost:8123](http://localhost:8123) in your browser
    2. Create your admin account (choose a username and strong password)
    3. Configure your location and units (metric/imperial)
    4. Complete the onboarding wizard
    5. You'll arrive at the Home Assistant dashboard
    """)

    if st.checkbox("✅ I have completed Home Assistant initial setup", key="check_ha_setup"):
        st.session_state.integration_progress["ha_setup"] = True
        st.success("Great! Now let's get the access token.")
        log_message("Home Assistant initial setup completed")

    st.markdown("---")

    # ==========================================================================
    # STEP 2: Generate Long-Lived Access Token
    # ==========================================================================
    st.subheader("2️⃣ Generate Long-Lived Access Token")

    st.info("""
    This token allows n8n and other services to control your Home Assistant.
    **Important:** You'll only see this token once, so copy it immediately!
    """)

    st.markdown("""
    **Steps:**
    1. In Home Assistant, click your **profile** (bottom left corner, shows your initials)
    2. Scroll down to the **Security** section
    3. Under **Long-Lived Access Tokens**, click **Create Token**
    4. Name it: `LCARS Computer` or `n8n`
    5. Click **OK**
    6. **IMMEDIATELY COPY THE TOKEN** (you won't see it again!)
    """)

    token_input = st.text_input(
        "📋 Paste your Long-Lived Access Token here:",
        type="password",
        help="This token will be saved to your .env file",
        key="token_input_field"
    )

    env_file = DOCKER_DIR / ".env"

    if token_input and st.button("💾 Save Token to .env File", type="primary"):
        try:
            # Read existing .env
            env_content = env_file.read_text(encoding='utf-8')

            # Replace the placeholder
            updated_content = env_content.replace(
                "HA_ACCESS_TOKEN=PASTE_YOUR_TOKEN_HERE",
                f"HA_ACCESS_TOKEN={token_input}"
            )

            # Write back
            env_file.write_text(updated_content, encoding='utf-8')

            st.success(f"✅ Token saved to `{env_file}`")
            st.session_state.integration_progress["ha_token"] = True
            st.session_state.environment_vars['HA_ACCESS_TOKEN'] = token_input
            log_message("Home Assistant token saved to .env file")

            # Auto-restart n8n
            with st.spinner("Restarting n8n to load new token..."):
                returncode, output = execute_command_with_output("docker compose restart n8n", cwd=DOCKER_DIR)
                if returncode == 0:
                    st.success("✅ n8n restarted with new token!")
                    log_message("n8n restarted successfully")

        except Exception as e:
            st.error(f"❌ Failed to update .env file: {e}")
            log_message(f"Failed to update .env: {e}", "ERROR")

    st.markdown("---")

    # ==========================================================================
    # STEP 3: Configure Open WebUI
    # ==========================================================================
    st.subheader("3️⃣ Configure Open WebUI & Pull LLM Model")

    deploy_config, services_config = _load_service_configs()
    open_webui_base_url = "http://localhost:3000"
    if deploy_config and services_config and "open-webui" in services_config:
        svc = services_config["open-webui"]
        open_webui_base_url = _format_base_url(svc.effective_host, svc.effective_port)

    st.markdown(f"""
    Now let's set up the LLM interface:

    1. Open [{open_webui_base_url}]({open_webui_base_url})
    2. **Sign up** (first user becomes admin - use the same credentials as HA if you want)
    3. Open WebUI should auto-detect Ollama running on port 11434
    4. Go to **Settings → Models** (top right profile icon → Settings → Models tab)
    5. In the **Pull a model** section, enter: `llama3.1:8b`
    6. Click **Pull** and wait 3-5 minutes (downloads ~4.7GB)
    7. Verify the model appears in your model list

    **Recommended models:**
    - `llama3.1:8b` - Best balance of speed and quality (4.7GB) ⭐ **RECOMMENDED**
    - `mistral:7b` - Faster but less capable (4.1GB)
    - `llama3.2:3b` - Very fast, good for testing (2GB)
    """)

    if st.checkbox("✅ I have configured Open WebUI and pulled llama3.1:8b", key="check_openwebui"):
        st.session_state.integration_progress["open_webui"] = True
        st.success("Excellent! The LLM is ready.")
        log_message("Open WebUI configured and model pulled")

    st.markdown("---")

    # ==========================================================================
    # STEP 4: Import LCARS Persona
    # ==========================================================================
    st.subheader("4️⃣ Import LCARS Computer Persona")

    st.info("""
    The LCARS persona transforms the generic LLM into your Star Trek computer. This is what makes it say
    "Affirmative" and "Acknowledged" instead of "Sure, I'd be happy to help!"
    """)

    # Read the persona file
    persona_file = PROJECT_ROOT / "prompts" / "lcars_persona.txt"
    persona_content = ""
    if persona_file.exists():
        persona_content = persona_file.read_text(encoding='utf-8')

    st.markdown(f"""
    **Steps:**
    1. In Open WebUI, click your profile icon (top right) → **Settings**
    2. Go to the **Personalization** tab
    3. Find **System Prompt** section
    4. Copy the entire LCARS persona below and paste it into the **System Prompt** field
    5. Click **Save**
    """)

    st.markdown("**LCARS Persona (click 'Copy to Clipboard' button):**")

    if persona_content:
        st.code(persona_content, language="text")

        # Use session state to avoid rerun issues
        if st.button("📋 Copy LCARS Persona to Clipboard", key="copy_persona"):
            st.info("Copy the text from the box above and paste it into Open WebUI's System Prompt field")
    else:
        st.error(f"❌ Could not find persona file at {persona_file}")

    if st.checkbox("✅ I have imported the LCARS persona into Open WebUI", key="check_persona"):
        st.session_state.integration_progress["lcars_persona"] = True
        st.success("Perfect! Your computer now has a personality.")
        log_message("LCARS persona imported")

    st.markdown("---")

    # ==========================================================================
    # STEP 5: Install HACS (Home Assistant Community Store)
    # ==========================================================================
    st.subheader("5️⃣ Install HACS (Required for Extended OpenAI)")

    st.warning("""
    ⚠️ **Critical Step:** HACS is required to install the Extended OpenAI Conversation integration,
    which is what allows the LLM to actually control your home. Without this, the voice commands won't work!
    """)

    st.markdown("""
    **What is HACS?** It's a custom repository manager for Home Assistant that gives you access to
    thousands of community integrations, including Extended OpenAI Conversation.

    **Installation method depends on your platform:**
    """)

    install_method = st.radio(
        "Choose your installation method:",
        ["Option 1: Terminal & SSH Add-on (Recommended)", "Option 2: Docker Exec Command"],
        key="hacs_install_method"
    )

    if "Terminal & SSH" in install_method:
        st.markdown("""
        **Option 1: Using Terminal & SSH Add-on (Easier)**

        1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
        2. Search for **Terminal & SSH** (official add-on)
        3. Click **Install** and wait for it to complete
        4. Click **Start** and enable **Show in sidebar**
        5. Click **Open Web UI** or find **Terminal** in the sidebar
        6. In the terminal, run this command:

        ```bash
        wget -O - https://get.hacs.xyz | bash -
        ```

        7. Wait for the installation to complete (~30 seconds)
        8. Restart Home Assistant: **Settings → System → Restart**
        9. Wait 2-3 minutes for Home Assistant to restart
        10. Refresh your browser
        """)

    else:
        st.markdown("""
        **Option 2: Using Docker Exec (Advanced)**

        If you prefer using the command line directly:
        """)

        command_box("""# Execute inside the Home Assistant container
docker exec -it homeassistant bash -c "wget -O - https://get.hacs.xyz | bash -"

# Then restart Home Assistant
cd docker
docker compose restart homeassistant""", "Run these commands:")

        if st.button("🔄 Restart Home Assistant Container", key="restart_ha_hacs"):
            with st.spinner("Restarting Home Assistant..."):
                returncode, output = execute_command_with_output("docker compose restart homeassistant", cwd=DOCKER_DIR)
                st.code(output, language="text")
                if returncode == 0:
                    st.success("✅ Home Assistant restarted! Wait 2-3 minutes for it to fully start.")
                    st.info("Refresh your Home Assistant web page after waiting.")

    st.markdown("""
    **After installation, verify HACS is working:**
    1. In Home Assistant, go to **Settings → Devices & Services**
    2. Click **+ Add Integration**
    3. Search for **HACS**
    4. If you see it, HACS is installed! ✅
    5. If not, wait another minute and refresh the page
    """)

    if st.checkbox("✅ I have installed HACS and can see it in the integrations list", key="check_hacs"):
        st.session_state.integration_progress["hacs"] = True
        st.success("Excellent! HACS is ready. Now we can install Extended OpenAI Conversation.")
        log_message("HACS installed successfully")

    st.markdown("---")

    # ==========================================================================
    # STEP 6: Install Extended OpenAI Conversation
    # ==========================================================================
    st.subheader("6️⃣ Install Extended OpenAI Conversation Integration")

    st.error("""
    🔴 **THIS IS THE MOST CRITICAL INTEGRATION!**
    This is what allows the LLM to control your lights, locks, climate, and all Home Assistant devices.
    Without this, you just have a chatbot that can't do anything.
    """)

    st.markdown("""
    **Steps to install via HACS:**

    1. In Home Assistant, open **HACS** (sidebar menu)
    2. Click **Integrations** at the top
    3. Click the **⋮** menu (top right) → **Custom repositories**
    4. Paste this URL: `https://github.com/jekalmin/extended_openai_conversation`
    5. Select Category: **Integration**
    6. Click **Add**
    7. Close the custom repositories dialog
    8. Click **+ Explore & Download Repositories** (bottom right)
    9. Search for: `Extended OpenAI Conversation`
    10. Click on it, then click **Download**
    11. Click **Download** again to confirm
    12. **Restart Home Assistant:** Settings → System → Restart
    13. Wait 2-3 minutes for restart to complete
    """)

    if st.button("🔄 Restart Home Assistant After Installing Integration", key="restart_ha_extended"):
        with st.spinner("Restarting Home Assistant..."):
            returncode, output = execute_command_with_output("docker compose restart homeassistant", cwd=DOCKER_DIR)
            st.code(output, language="text")
            if returncode == 0:
                st.success("✅ Home Assistant restarting! Wait 2-3 minutes, then refresh the page.")

    if st.checkbox("✅ I have installed Extended OpenAI Conversation via HACS and restarted HA", key="check_extended"):
        st.session_state.integration_progress["extended_openai"] = True
        st.success("Perfect! Now let's configure it.")
        log_message("Extended OpenAI Conversation installed")

    st.markdown("---")

    # ==========================================================================
    # STEP 7: Configure Extended OpenAI Conversation
    # ==========================================================================
    st.subheader("7️⃣ Configure Extended OpenAI Conversation with LCARS Tools")

    st.info("""
    Now we'll configure the integration to connect to your local Ollama server and give it the ability
    to control your home through function calling (the 12 LCARS tools).
    """)

    st.markdown("""
    **Part A: Add the Integration**

    1. In Home Assistant, go to **Settings → Devices & Services**
    2. Click **+ Add Integration** (bottom right)
    3. Search for: `Extended OpenAI Conversation`
    4. Click on it to add it
    5. Give it a name: `LCARS Computer` (or leave default)
    6. Click **Submit**
    """)

    st.markdown("""
    **Part B: Configure API Connection**

    1. After adding, click **Configure** on the Extended OpenAI Conversation card
    2. Enter these values:

    **API Configuration:**
    - **Base URL:** `http://host.docker.internal:3000/v1` (critical - don't use localhost!)
    - **API Key:** (Leave blank or enter any text - local Ollama doesn't need it)
    - **Model:** `llama3.1:8b` (or whatever model you pulled)
    - **Max Tokens:** `2048`
    - **Temperature:** `0.7`
    - **Top P:** `0.95`
    """)

    st.code("""Base URL: http://host.docker.internal:3000/v1
API Key: (leave blank)
Model: llama3.1:8b
Max Tokens: 2048
Temperature: 0.7
Top P: 0.95""", language="text")

    st.markdown("""
    **Part C: Add LCARS Tools (Function Calling)**

    This is the magic step that gives the LLM control over your home!

    1. In the same configuration dialog, find the **Functions** or **Tools** section
    2. Look for a field called **Spec** or **Function Definitions**
    3. Copy the tool definitions from the code box below
    4. Paste them into the **Spec** field
    5. Click **Submit**
    """)

    # Read the tools from extended_openai.yaml
    tools_file = PROJECT_ROOT / "homeassistant" / "config" / "extended_openai.yaml"
    tools_content = ""
    if tools_file.exists():
        # Extract just the spec section (lines 54-353)
        full_content = tools_file.read_text(encoding='utf-8')
        lines = full_content.split('\n')
        # Find the start of spec definitions
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('- spec:'):
                start_idx = i
                break
        if start_idx:
            # Extract from first spec to before the END marker
            end_idx = None
            for i, line in enumerate(lines):
                if '# --- END SPEC CONFIGURATION ---' in line:
                    end_idx = i
                    break
            if end_idx:
                tools_content = '\n'.join(lines[start_idx:end_idx])

    st.markdown("**LCARS Tool Definitions (copy all of this):**")
    if tools_content:
        st.code(tools_content, language="yaml")
        st.info("📋 Copy the YAML above and paste it into the 'Spec' field in Extended OpenAI Conversation settings")
    else:
        st.error(f"❌ Could not load tools from {tools_file}")
        st.markdown("**Manual alternative:** Open `homeassistant/config/extended_openai.yaml` and copy lines 54-353")

    st.markdown("""
    **Part D: Set as Preferred Agent**

    1. Go to **Settings → Voice assistants → Assist**
    2. Click on your assistant (usually named "Home Assistant")
    3. Under **Conversation agent**, select **Extended OpenAI Conversation**
    4. Click **Update**
    """)

    if st.checkbox("✅ I have configured Extended OpenAI with tools and set it as the conversation agent", key="check_extended_config"):
        st.session_state.integration_progress["extended_openai_config"] = True
        st.success("🎉 CRITICAL INTEGRATION COMPLETE! The LLM can now control your home!")
        log_message("Extended OpenAI Conversation configured with tools")

    st.markdown("---")

    # ==========================================================================
    # STEP 8: Import n8n Workflows
    # ==========================================================================
    st.subheader("8️⃣ Import n8n Workflows")

    st.info("""
    n8n handles complex workflows and fire-and-forget tasks. We'll import 4 pre-built workflows:
    - **Voice Command Handler** - Main processing pipeline
    - **Red Alert Protocol** - Emergency lighting and alerts
    - **Status Report** - Comprehensive home status
    - **Deep Research Agent** - Long-running research tasks
    """)

    deploy_config_obj, services_config = _load_service_configs()
    n8n_base_url = "http://localhost:5678"
    if deploy_config_obj and services_config and "n8n" in services_config:
        svc = services_config["n8n"]
        n8n_base_url = _format_base_url(svc.effective_host, svc.effective_port)

    st.markdown(f"""
    **Steps:**

    1. Open [{n8n_base_url}]({n8n_base_url}) in your browser
    2. Create an account (if not already done)
    3. You'll see an empty workspace

    **For each workflow file:**

    4. Click **Workflows** in the left sidebar
    5. Click the **⋮** menu → **Import from File**
    6. Navigate to the `n8n/workflows/` directory in your LCARS Computer folder
    7. Import these files one by one:
       - `voice_command_handler.json`
       - `red_alert_protocol.json`
       - `status_report.json`
       - `deep_research_agent.json`
    8. After importing each, click **Save** and **Activate** (toggle in top right)

    **Workflow locations:**
    - Full path: `{PROJECT_ROOT / 'n8n' / 'workflows'}`
    """)

    st.markdown("""
    **After importing, verify:**
    - You should see 4 workflows in the n8n sidebar
    - Each should have a green "Active" toggle
    """)

    if st.checkbox("✅ I have imported all 4 n8n workflows and activated them", key="check_n8n"):
        st.session_state.integration_progress["n8n_workflows"] = True
        st.success("Excellent! n8n is ready to orchestrate complex tasks.")
        log_message("n8n workflows imported and activated")

    st.markdown("---")

    # ==========================================================================
    # STEP 9: Configure Assist Pipeline (Voice Control)
    # ==========================================================================
    st.subheader("9️⃣ Configure Assist Pipeline for Voice Control (Optional)")

    st.info("""
    **This step is OPTIONAL** and only needed if you plan to use voice satellites with wake word detection.
    If you just want to control your home via the web interface or test with text first, you can skip this.
    """)

    st.markdown("""
    **What is the Assist Pipeline?**
    It connects your voice satellites (ESP32 devices) to the complete voice processing chain:
    - **Wake Word** (openWakeWord) - Detects the wake phrase (e.g., "Computer")
    - **STT** (Whisper) - Converts speech to text
    - **Conversation** (Extended OpenAI) - LLM processes the command
    - **TTS** (Piper) - Converts response to speech

    ---
    ## Option A (Recommended): "Computer" wake word via on-prem openWakeWord container

    This repo ships an on-prem wake word service: `openwakeword` (Wyoming protocol) on port 10400.
    To make the wake phrase actually be **"Computer"**, you must install (or train) a wake word model
    named `computer` that is compatible with openWakeWord.

    **Steps:**
    1. Put your wake word model files into: `docker/volumes/openwakeword/`
         - This folder is mounted into the container at `/custom`.
    2. Set `OPENWAKEWORD_PRELOAD_MODEL=computer` in `docker/.env`.
    3. Restart the `openwakeword` container so it loads the model.

    """, unsafe_allow_html=False)

    command_box(
        """# 1) Put your custom model in the mounted folder
ls -la docker/volumes/openwakeword/

# 2) Set the model name in docker/.env
sed -i 's/^OPENWAKEWORD_PRELOAD_MODEL=.*/OPENWAKEWORD_PRELOAD_MODEL=computer/' docker/.env

# 3) Restart only the wake word service
cd docker && docker compose restart openwakeword
""",
        "Option A: enable the 'computer' wake word model",
    )

    if st.button("🔄 Restart openWakeWord container", key="restart_openwakeword"):
        with st.spinner("Restarting openWakeWord..."):
            returncode, output = execute_command_with_output("docker compose restart openwakeword", cwd=DOCKER_DIR)
            st.code(output, language="text")
            if returncode == 0:
                st.success("✅ openWakeWord restarted")
                log_message("openWakeWord restarted via UI")
            else:
                st.error("❌ Failed to restart openWakeWord")
                log_message("Failed to restart openWakeWord", "ERROR")

    st.markdown("""
    **Verify model load:**
    - View logs: `cd docker && docker compose logs --tail=200 openwakeword`

    ---
    ## Configure the Assist Pipeline

    1. In Home Assistant, go to **Settings → Voice assistants → Assist**
    2. Click **+ Add Pipeline** (or edit the default one)
    3. Configure these settings:

    **Pipeline Configuration:**
    - **Name:** `LCARS Voice Pipeline`
    - **Language:** `English`
    - **Conversation Agent:** `Extended OpenAI Conversation` (the one we just configured!)
    - **Wake Word:**
        - **Linux default (Home Assistant is host-networked):** `tcp://127.0.0.1:10400`
        - **Docker Desktop / HA not host-networked:** `tcp://host.docker.internal:10400`
    - **Speech-to-Text:**
        - **Linux default:** `tcp://127.0.0.1:10300`
        - **Docker Desktop / HA not host-networked:** `tcp://host.docker.internal:10300`
    - **Text-to-Speech:**
        - **Linux default:** `tcp://127.0.0.1:10200`
        - **Docker Desktop / HA not host-networked:** `tcp://host.docker.internal:10200`

    4. Click **Create** or **Update**
    5. Set as default pipeline if desired
    """)

    st.code("""Name: LCARS Voice Pipeline
Language: English
Conversation Agent: Extended OpenAI Conversation
Wake Word (Linux): tcp://127.0.0.1:10400
Speech-to-Text (Linux): tcp://127.0.0.1:10300
Text-to-Speech (Linux): tcp://127.0.0.1:10200""", language="text")

    st.markdown("""
    **Voice Satellite Setup (Advanced):**

    If you have ESP32-S3-BOX-3 or M5Stack Atom Echo hardware:
    1. Flash ESPHome firmware using configs in `esphome/` directory
    2. Add the satellite to Home Assistant via ESPHome integration
    3. Assign it to the LCARS Voice Pipeline
    4. Say "Computer, turn on the lights" and watch the magic! ✨

    See `docs/ESPHOME_SATELLITE_SETUP.md` for detailed instructions.
    """)

    if st.checkbox("✅ I have configured the Assist Pipeline (or will skip voice for now)", key="check_assist"):
        st.session_state.integration_progress["assist_pipeline"] = True
        st.success("Pipeline configured! You're ready for voice control.")
        log_message("Assist Pipeline configured")

    st.markdown("---")

    # ==========================================================================
    # FINAL STATUS
    # ==========================================================================
    st.subheader("🎉 Integration Complete!")

    if all(st.session_state.integration_progress.values()):
        st.success("""
        ✅ **ALL INTEGRATIONS COMPLETE!**

        Your LCARS Computer is now fully operational! You have:
        - ✅ Home Assistant running with admin access
        - ✅ LLM (Ollama) with LCARS persona
        - ✅ Extended OpenAI Conversation with 12 control tools
        - ✅ n8n workflows ready for complex tasks
        - ✅ Assist Pipeline configured (if using voice)

        **Next Steps:**
        1. Proceed to **Verification** to test the system
        2. Try your first command: "Turn on the living room lights"
        3. Enjoy your Star Trek-inspired smart home! 🖖
        """)
        log_message("All integration steps completed!")
    else:
        remaining = [name for key, name in integration_steps.items()
                    if not st.session_state.integration_progress[key]]
        st.warning(f"""
        ⚠️ **Integration {completed_steps}/{total_steps} complete**

        Remaining steps:
        {chr(10).join('- ' + step for step in remaining)}

        Complete all steps before proceeding to Verification.
        """)

# --- SECTION: VERIFICATION ---
elif step_name == "Verification":
    st.title("✅ Verification")
    st.markdown("### System Health Check")

    log_message("User accessed Verification section")

    st.info("Let's verify all services are running and can communicate with each other.")

    if st.button("🩺 Run Health Check", type="primary"):
        with st.spinner("Checking all services..."):
            log_message("Running health check")

            results = {}

            deploy_config, services_config = _load_service_configs()
            if deploy_config is None or services_config is None:
                st.error("❌ Unable to load deployment configuration for health checks")
                log_message("Health check failed: deploy_config module unavailable", "ERROR")
            else:
                for service_key in HEALTH_CHECK_SERVICE_KEYS:
                    service = services_config.get(service_key)
                    if not service:
                        continue

                    st.subheader(f"🔍 {service.name}")

                    try:
                        start_time = time.time()
                        is_healthy, error_msg = deploy_config.check_service_health(service)
                        elapsed = (time.time() - start_time) * 1000

                        endpoint = _format_base_url(service.effective_host, service.effective_port)

                        if is_healthy:
                            status_indicator("success", f"✅ Online ({endpoint}) - {elapsed:.0f}ms")
                            results[service_key] = True
                            log_message(f"{service.name} health check passed")
                        else:
                            status_indicator("error", f"❌ Offline ({endpoint}) - {error_msg or 'unknown error'}")
                            results[service_key] = False
                            log_message(f"{service.name} is offline: {error_msg}", "ERROR")

                    except Exception as e:
                        status_indicator("error", f"❌ Error: {e}")
                        results[service_key] = False
                        log_message(f"{service.name} check failed: {e}", "ERROR")

            st.markdown("---")

            # Summary
            healthy_count = sum(results.values())
            total_count = len(results)

            if healthy_count == total_count:
                st.success(f"🎉 All systems operational! ({healthy_count}/{total_count})")
                log_message("All health checks passed")
                st.balloons()
            elif healthy_count >= total_count - 1:
                st.warning(f"⚠️ Most systems online ({healthy_count}/{total_count}). Review failed services above.")
                log_message(f"Health check: {healthy_count}/{total_count} passed", "WARNING")
            else:
                st.error(f"❌ Multiple services offline ({healthy_count}/{total_count}). Check Docker logs.")
                log_message(f"Health check failed: {healthy_count}/{total_count}", "ERROR")

    st.markdown("---")

    st.subheader("📋 Troubleshooting Failed Services")

    with st.expander("🔍 View Container Logs"):
        selected_service = st.selectbox(
            "Select a service to view logs:",
            ["homeassistant", "n8n", "open-webui", "ollama", "whisper", "piper", "openwakeword", "postgres", "redis"]
        )

        if st.button(f"📄 Show {selected_service} logs"):
            returncode, output = execute_command_with_output(f"docker compose logs --tail=50 {selected_service}", cwd=DOCKER_DIR)
            st.code(output, language="text")
            log_message(f"Viewed logs for {selected_service}")

# --- SECTION: OPERATIONS ---
elif step_name == "Operations":
    st.title("🎮 Operations & Daily Usage")
    st.markdown("### Managing Your LCARS Computer")

    log_message("User accessed Operations section")

    st.success("🎉 Congratulations! Your LCARS Computer is operational.")

    # Service Access Points
    st.subheader("🌐 Service Access Points")

    deploy_config, services_config = _load_service_configs()
    ha_url = "http://localhost:8123"
    n8n_url = "http://localhost:5678"
    open_webui_url = "http://localhost:3000"
    ollama_url = "http://localhost:11434"

    if deploy_config and services_config:
        if "homeassistant" in services_config:
            svc = services_config["homeassistant"]
            ha_url = _format_base_url(svc.effective_host, svc.effective_port)
        if "n8n" in services_config:
            svc = services_config["n8n"]
            n8n_url = _format_base_url(svc.effective_host, svc.effective_port)
        if "open-webui" in services_config:
            svc = services_config["open-webui"]
            open_webui_url = _format_base_url(svc.effective_host, svc.effective_port)
        if "ollama" in services_config:
            svc = services_config["ollama"]
            ollama_url = _format_base_url(svc.effective_host, svc.effective_port)

    services_table = """
    | Service | URL | Purpose |
    |---------|-----|---------|
    | 🏠 Home Assistant | [{ha_url}]({ha_url}) | Device control and automation |
    | ⚡ n8n | [{n8n_url}]({n8n_url}) | Workflow orchestration |
    | 🧠 Open WebUI | [{open_webui_url}]({open_webui_url}) | Chat with LCARS AI |
    | 🤖 Ollama API | [{ollama_url}]({ollama_url}) | LLM inference endpoint |
    """
    st.markdown(services_table.format(
        ha_url=ha_url,
        n8n_url=n8n_url,
        open_webui_url=open_webui_url,
        ollama_url=ollama_url,
    ))

    st.markdown("---")

    # Common Operations
    st.subheader("⚙️ Common Operations")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🛑 Stop", "▶️ Start", "🔄 Restart", "📊 Status", "🗑️ Cleanup"])

    with tab1:
        st.markdown("### Stop All Services")
        st.markdown("This gracefully shuts down all containers:")

        command_box("cd docker && docker compose down", "Stop the entire stack:")

        if st.button("🛑 Stop LCARS Computer"):
            with st.spinner("Stopping services..."):
                returncode, output = execute_command_with_output("docker compose down", cwd=DOCKER_DIR)
                st.code(output, language="text")

                if returncode == 0:
                    st.success("✅ All services stopped")
                    log_message("Services stopped via UI")
                else:
                    st.error("❌ Failed to stop services")
                    log_message("Failed to stop services", "ERROR")

    with tab2:
        st.markdown("### Start All Services")
        st.markdown("This starts all containers:")

        command_box("cd docker && docker compose up -d", "Start the stack:")

        if st.button("▶️ Start LCARS Computer"):
            with st.spinner("Starting services..."):
                returncode, output = execute_command_with_output("docker compose up -d", cwd=DOCKER_DIR)
                st.code(output, language="text")

                if returncode == 0:
                    st.success("✅ All services started")
                    log_message("Services started via UI")
                else:
                    st.error("❌ Failed to start services")
                    log_message("Failed to start services", "ERROR")

    with tab3:
        st.markdown("### Restart Services")

        restart_all = st.checkbox("Restart all services")

        if restart_all:
            if st.button("🔄 Restart All"):
                with st.spinner("Restarting..."):
                    returncode, output = execute_command_with_output("docker compose restart", cwd=DOCKER_DIR)
                    st.code(output, language="text")
                    log_message("Restarted all services")
        else:
            service_to_restart = st.selectbox(
                "Select a service to restart:",
                ["homeassistant", "n8n", "open-webui", "ollama", "whisper", "piper"]
            )

            if st.button(f"🔄 Restart {service_to_restart}"):
                with st.spinner(f"Restarting {service_to_restart}..."):
                    returncode, output = execute_command_with_output(f"docker compose restart {service_to_restart}", cwd=DOCKER_DIR)
                    st.code(output, language="text")
                    log_message(f"Restarted {service_to_restart}")

    with tab4:
        st.markdown("### Container Status")

        if st.button("📊 Check Status"):
            returncode, output = execute_command_with_output("docker compose ps", cwd=DOCKER_DIR)
            st.code(output, language="text")
            log_message("Checked container status")

    with tab5:
        st.markdown("### 🗑️ Complete Installation Cleanup")

        st.warning("""
        ⚠️ **WARNING**: This will completely remove the LCARS Computer installation and ALL data.

        This is useful for:
        - Starting fresh after testing
        - Troubleshooting installation issues
        - Removing the system completely
        """)

        st.markdown("---")

        st.markdown("#### What will be removed:")

        cleanup_options = {
            "containers": st.checkbox("🐳 Stop and remove all LCARS containers", value=True, help="Stops and removes all Docker containers created by LCARS"),
            "volumes": st.checkbox("💾 Delete all volumes (⚠️ ALL DATA LOSS)", value=False, help="Removes all data: databases, configurations, models, etc."),
            "images": st.checkbox("🖼️ Remove Docker images", value=False, help="Removes downloaded Docker images (can be re-downloaded)"),
            "networks": st.checkbox("🌐 Remove Docker networks", value=False, help="Removes the LCARS network"),
            "env_file": st.checkbox("🔐 Delete .env file", value=False, help="Removes the environment file with secrets"),
            "config_files": st.checkbox("📝 Delete generated config files", value=False, help="Removes deployment_config.json and docker-compose.override.yml"),
            "logs": st.checkbox("📄 Clear installation logs", value=False, help="Removes installation log files"),
        }

        st.markdown("---")

        # Preview what will be removed
        with st.expander("📋 Preview Cleanup Actions"):
            st.markdown("**The following commands will be executed:**")

            commands = []

            if cleanup_options["containers"]:
                commands.append("# Stop and remove all containers")
                commands.append("docker compose down")

            if cleanup_options["volumes"]:
                commands.append("\n# Remove all volumes (DATA LOSS)")
                commands.append("docker compose down -v")
                commands.append("rm -rf docker/volumes/*")

            if cleanup_options["images"]:
                commands.append("\n# Remove Docker images")
                commands.append("docker compose down --rmi all")

            if cleanup_options["networks"]:
                commands.append("\n# Remove networks")
                commands.append("docker network rm lcars_network")

            if cleanup_options["env_file"]:
                commands.append("\n# Remove .env file")
                commands.append("rm docker/.env")

            if cleanup_options["config_files"]:
                commands.append("\n# Remove generated config files")
                commands.append("rm docker/deployment_config.json")
                commands.append("rm docker/docker-compose.override.yml")

            if cleanup_options["logs"]:
                commands.append("\n# Clear logs")
                commands.append("rm logs/install_*.log")

            if commands:
                st.code("\n".join(commands), language="bash")
            else:
                st.info("No cleanup options selected")

        st.markdown("---")

        # Confirmation
        st.error("🚨 **DANGER ZONE** 🚨")

        confirm_text = st.text_input(
            'Type "DELETE EVERYTHING" to confirm complete cleanup:',
            key="cleanup_confirm"
        )

        cleanup_enabled = confirm_text == "DELETE EVERYTHING" and any(cleanup_options.values())

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ Execute Cleanup", type="primary", disabled=not cleanup_enabled):
                if cleanup_enabled:
                    with st.spinner("Cleaning up LCARS installation..."):
                        log_message("Starting complete cleanup", "WARNING")

                        results = []

                        # 1. Stop and remove containers
                        if cleanup_options["containers"] or cleanup_options["volumes"] or cleanup_options["images"]:
                            compose_down_flags = []
                            if cleanup_options["volumes"]:
                                compose_down_flags.append("-v")
                            if cleanup_options["images"]:
                                compose_down_flags.append("--rmi all")

                            cmd = f"docker compose down {' '.join(compose_down_flags)}"
                            returncode, output = execute_command_with_output(cmd, cwd=DOCKER_DIR)
                            results.append(("Containers/Volumes/Images", returncode == 0, output))
                            log_message(f"Removed containers: {returncode == 0}")

                        # 2. Remove volume directories
                        if cleanup_options["volumes"]:
                            volumes_dir = DOCKER_DIR / "volumes"
                            if volumes_dir.exists():
                                import shutil
                                try:
                                    shutil.rmtree(volumes_dir)
                                    volumes_dir.mkdir(exist_ok=True)
                                    results.append(("Volume directories", True, "Removed all volume data"))
                                    log_message("Removed volume directories")
                                except Exception as e:
                                    results.append(("Volume directories", False, str(e)))
                                    log_message(f"Failed to remove volumes: {e}", "ERROR")

                        # 3. Remove networks
                        if cleanup_options["networks"]:
                            returncode, output = execute_command_with_output("docker network rm lcars_network")
                            results.append(("Networks", returncode == 0, output))
                            log_message(f"Removed networks: {returncode == 0}")

                        # 4. Remove .env file
                        if cleanup_options["env_file"]:
                            env_file = DOCKER_DIR / ".env"
                            if env_file.exists():
                                env_file.unlink()
                                results.append((".env file", True, "Removed"))
                                log_message("Removed .env file")

                        # 5. Remove config files
                        if cleanup_options["config_files"]:
                            config_path = DOCKER_DIR / "deployment_config.json"
                            override_path = DOCKER_DIR / "docker-compose.override.yml"

                            if config_path.exists():
                                config_path.unlink()
                            if override_path.exists():
                                override_path.unlink()

                            results.append(("Config files", True, "Removed"))
                            log_message("Removed config files")

                        # 6. Clear logs
                        if cleanup_options["logs"]:
                            logs_dir = PROJECT_ROOT / "logs"
                            if logs_dir.exists():
                                for log_file in logs_dir.glob("install_*.log"):
                                    log_file.unlink()
                                results.append(("Log files", True, "Cleared"))
                                log_message("Cleared log files")

                        # 7. Reset session state
                        st.session_state.deployment_mode = None
                        st.session_state.deployment_config = None
                        st.session_state.deployment_service_health = {}
                        st.session_state.deployment_last_discovery = None

                        # Show results
                        st.markdown("### Cleanup Results:")

                        for item, success, output in results:
                            if success:
                                st.success(f"✅ {item}: Removed")
                            else:
                                st.error(f"❌ {item}: Failed")

                            with st.expander(f"Details: {item}"):
                                st.code(output, language="text")

                        st.success("🎉 Cleanup completed! LCARS Computer has been removed.")
                        log_message("Cleanup completed", "WARNING")

                        st.info("💡 You can now run the installation again from the beginning.")

        with col2:
            if st.button("❌ Cancel"):
                st.info("Cleanup cancelled")

    st.markdown("---")

    # Updates
    st.subheader("🔄 System Updates")

    st.markdown("""
    To update the LCARS Computer to the latest version:
    """)

    command_box("""# Pull latest code
git pull

# Update containers
cd docker
docker compose pull
docker compose up -d

# Or use the update script (Linux)
./scripts/update.sh""", "Update commands:")

    st.markdown("---")

    # Backups
    st.subheader("💾 Backups")

    st.markdown("""
    **What to backup:**
    - `docker/.env` (your environment variables and secrets)
    - `docker/volumes/homeassistant/` (Home Assistant configuration)
    - `docker/volumes/n8n/` (n8n workflows)
    - `docker/volumes/postgres/` (database)
    """)

    command_box("python scripts/backup.py", "Run the backup script:")

    st.markdown("---")

    st.success("✅ You are now ready to use the LCARS Computer! Live long and prosper. 🖖")
    log_message("User completed installation guide")

# =============================================================================
# PERSISTENT CLI LOG (shown on all pages)
# =============================================================================
st.markdown("---")
render_cli_log()
