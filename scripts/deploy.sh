 #!/usr/bin/env bash
#
# LCARS Computer - Automated Deployment Script
# 
# This script automates the deployment of the complete Star Trek voice assistant
# stack on a Linux system. It handles Docker installation, configuration file
# setup, volume creation, and initial service startup.
#
# OS notes:
#   - Primary target: Linux Mint Xia (Ubuntu-based) / Ubuntu / Debian using Docker Engine.
#   - Windows/macOS: Use Docker Desktop and run the stack manually (see docs/DOCKER_INSTALL.md and README).
#
# Prerequisites:
#   - Linux system (tested on Ubuntu 22.04, Debian 12, Linux Mint)
#   - sudo/root access
#   - Internet connection for pulling Docker images
#
# Usage:
#   ./deploy.sh [options]
#
# Options:
#   --gpu          Enable NVIDIA GPU support for LLM acceleration
#   --dev          Development mode (exposes all ports, verbose logging)
#   --no-pull      Skip pulling latest Docker images
#   --help         Show this help message

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_DIR/docker"
LOG_FILE="$PROJECT_DIR/deploy.log"

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
GPU_ENABLED=false
DEV_MODE=false
PULL_IMAGES=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            GPU_ENABLED=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --no-pull)
            PULL_IMAGES=false
            shift
            ;;
        --help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Logging function that writes to both console and log file
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        STEP)
            echo -e "\n${BLUE}=== $message ===${NC}\n"
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check system requirements
check_requirements() {
    log STEP "Checking System Requirements"
    
    # Check for minimum RAM (8GB recommended)
    local total_ram=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $total_ram -lt 8 ]]; then
        log WARN "System has ${total_ram}GB RAM. 8GB+ recommended for LLM inference."
    else
        log INFO "RAM check passed: ${total_ram}GB available"
    fi
    
    # Check for disk space (50GB minimum)
    local free_space=$(df -BG "$PROJECT_DIR" | awk 'NR==2 {print $4}' | tr -d 'G')
    if [[ $free_space -lt 50 ]]; then
        log WARN "Only ${free_space}GB disk space available. 50GB+ recommended."
    else
        log INFO "Disk space check passed: ${free_space}GB available"
    fi
    
    # Check for NVIDIA GPU if --gpu flag was passed
    if [[ "$GPU_ENABLED" == true ]]; then
        if command_exists nvidia-smi; then
            local gpu_info=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "Unknown")
            log INFO "NVIDIA GPU detected: $gpu_info"
        else
            log ERROR "GPU mode requested but nvidia-smi not found."
            log INFO "Install NVIDIA drivers and NVIDIA Container Toolkit first."
            exit 1
        fi
    fi
}

# Install Docker if not present
install_docker() {
    log STEP "Checking Docker Installation"
    
    if command_exists docker; then
        local docker_version=$(docker --version | cut -d' ' -f3 | tr -d ',')
        log INFO "Docker already installed: v$docker_version"
    else
        log INFO "Docker not found. Installing..."
        
        # Install Docker using the official convenience script
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo sh /tmp/get-docker.sh
        rm /tmp/get-docker.sh
        
        # Add current user to docker group
        sudo usermod -aG docker "$USER"
        
        log INFO "Docker installed successfully."
        log WARN "You may need to log out and back in for group changes to take effect."
    fi
    
    # Check Docker Compose
    if docker compose version &> /dev/null; then
        local compose_version=$(docker compose version --short)
        log INFO "Docker Compose available: v$compose_version"
    else
        log ERROR "Docker Compose not found. It should be included with Docker."
        exit 1
    fi
    
    # Ensure Docker service is running
    if ! sudo systemctl is-active --quiet docker; then
        log INFO "Starting Docker service..."
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
}

# Install NVIDIA Container Toolkit for GPU support
install_nvidia_toolkit() {
    if [[ "$GPU_ENABLED" != true ]]; then
        return 0
    fi
    
    log STEP "Setting Up NVIDIA Container Toolkit"
    
    if dpkg -l | grep -q nvidia-container-toolkit; then
        log INFO "NVIDIA Container Toolkit already installed."
        return 0
    fi
    
    log INFO "Installing NVIDIA Container Toolkit..."
    
    # Add NVIDIA repository
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    
    # Install the toolkit
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    
    # Configure Docker to use NVIDIA runtime
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
    
    log INFO "NVIDIA Container Toolkit installed and configured."
}

# Create required directories and volumes
setup_directories() {
    log STEP "Setting Up Directory Structure"
    
    local directories=(
        "$DOCKER_DIR/volumes/homeassistant"
        "$DOCKER_DIR/volumes/n8n"
        "$DOCKER_DIR/volumes/n8n_files"
        "$DOCKER_DIR/volumes/ollama"
        "$DOCKER_DIR/volumes/open-webui"
        "$DOCKER_DIR/volumes/postgres"
        "$DOCKER_DIR/volumes/redis"
        "$DOCKER_DIR/volumes/whisper"
        "$DOCKER_DIR/volumes/piper"
        "$DOCKER_DIR/volumes/openwakeword"
        "$PROJECT_DIR/homeassistant/config/sounds"
        "$PROJECT_DIR/homeassistant/config/themes"
        "$PROJECT_DIR/homeassistant/config/packages"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log INFO "Created directory: $dir"
        fi
    done
    
    # Set permissions for docker volumes
    sudo chown -R 1000:1000 "$DOCKER_DIR/volumes/n8n" 2>/dev/null || true
    
    log INFO "Directory structure ready."
}

# Generate secure passwords and create .env file
setup_environment() {
    log STEP "Configuring Environment Variables"
    
    local env_file="$DOCKER_DIR/.env"
    
    if [[ -f "$env_file" ]]; then
        log WARN ".env file already exists. Backing up to .env.backup"
        cp "$env_file" "$env_file.backup"
    fi
    
    # Generate secure random values
    local postgres_password=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
    local n8n_encryption_key=$(openssl rand -hex 32)
    local webui_secret_key=$(openssl rand -hex 32)
    
    # Detect timezone
    local timezone="America/New_York"
    if [[ -f /etc/timezone ]]; then
        timezone=$(cat /etc/timezone)
    elif [[ -L /etc/localtime ]]; then
        timezone=$(readlink /etc/localtime | sed 's|.*/zoneinfo/||')
    fi
    
    # Create the .env file
    cat > "$env_file" << EOF
# LCARS Computer - Environment Configuration
# Generated on $(date)
# 
# WARNING: This file contains secrets. Do not commit to version control.

# General Settings
TIMEZONE=$timezone

# n8n Configuration
N8N_HOST=localhost
WEBHOOK_URL=http://localhost:5678/
N8N_ENCRYPTION_KEY=$n8n_encryption_key

# Database Configuration
POSTGRES_PASSWORD=$postgres_password

# Open WebUI Configuration
WEBUI_SECRET_KEY=$webui_secret_key

# Home Assistant (to be filled after HA setup)
HA_ACCESS_TOKEN=

# Whisper Configuration
WHISPER_MODEL=medium-int8

# Piper TTS Voice
PIPER_VOICE=en_US-amy-medium
EOF
    
    # Restrict permissions on .env file
    chmod 600 "$env_file"
    
    log INFO "Environment file created at $env_file"
    log INFO "Generated secure passwords and encryption keys."
}

# Copy Home Assistant configuration files
setup_homeassistant_config() {
    log STEP "Setting Up Home Assistant Configuration"
    
    local ha_config_src="$PROJECT_DIR/homeassistant/config"
    local ha_config_dst="$DOCKER_DIR/volumes/homeassistant"
    
    # Copy configuration files if they don't exist in the volume
    if [[ ! -f "$ha_config_dst/configuration.yaml" ]]; then
        cp "$ha_config_src/configuration.yaml" "$ha_config_dst/"
        log INFO "Copied configuration.yaml"
    fi
    
    if [[ ! -f "$ha_config_dst/scripts.yaml" ]]; then
        cp "$ha_config_src/scripts.yaml" "$ha_config_dst/"
        log INFO "Copied scripts.yaml"
    fi
    
    # Create empty files for included configs
    touch "$ha_config_dst/automations.yaml"
    touch "$ha_config_dst/scenes.yaml"
    touch "$ha_config_dst/groups.yaml"
    touch "$ha_config_dst/customize.yaml"
    
    log INFO "Home Assistant configuration files in place."
}

# Apply GPU configuration to docker-compose if needed
configure_gpu_support() {
    if [[ "$GPU_ENABLED" != true ]]; then
        return 0
    fi
    
    log STEP "Enabling GPU Support in Docker Compose"
    
    local compose_file="$DOCKER_DIR/docker-compose.yml"
    local compose_gpu_file="$DOCKER_DIR/docker-compose.gpu.yml"
    
    # Create GPU override file
    cat > "$compose_gpu_file" << 'EOF'
# GPU Override Configuration for LCARS Computer
# This file enables NVIDIA GPU support for Ollama and Whisper

services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      
  whisper:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
EOF
    
    log INFO "Created GPU override file: $compose_gpu_file"
    log INFO "GPU support will be enabled when starting containers."
}

# Start the Docker stack
start_services() {
    log STEP "Starting LCARS Computer Services"
    
    cd "$DOCKER_DIR"
    
    # Pull latest images if requested
    if [[ "$PULL_IMAGES" == true ]]; then
        log INFO "Pulling latest Docker images (this may take a while)..."
        if [[ "$GPU_ENABLED" == true ]]; then
            docker compose -f docker-compose.yml -f docker-compose.gpu.yml pull
        else
            docker compose pull
        fi
    fi
    
    # Start services
    log INFO "Starting services..."
    if [[ "$GPU_ENABLED" == true ]]; then
        local compose_args=("-f" "docker-compose.yml" "-f" "docker-compose.gpu.yml")
        if [[ -f "docker-compose.override.yml" ]]; then
            compose_args+=("-f" "docker-compose.override.yml")
        fi
        docker compose "${compose_args[@]}" up -d
    else
        docker compose up -d
    fi
    
    log INFO "Waiting for services to initialize..."
    sleep 10
    
    # Check service health
    log INFO "Checking service status..."
    docker compose ps
}

# Pull default Ollama model
setup_ollama_model() {
    log STEP "Setting Up Default LLM Model"
    
    log INFO "Waiting for Ollama to be ready..."
    local max_attempts=30
    local attempt=1
    
    while ! curl -s http://localhost:11434/api/tags &> /dev/null; do
        if [[ $attempt -ge $max_attempts ]]; then
            log WARN "Ollama not responding. You can pull models manually later."
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    
    log INFO "Pulling llama3.1:8b model (this will take several minutes)..."
    docker exec ollama ollama pull llama3.1:8b || {
        log WARN "Failed to pull model. You can try manually: docker exec ollama ollama pull llama3.1:8b"
    }
    
    log INFO "Model setup complete."
}

# Print post-installation instructions
print_instructions() {
    log STEP "Deployment Complete!"
    
    echo -e "\n${GREEN}=========================================${NC}"
    echo -e "${GREEN}   LCARS COMPUTER DEPLOYMENT COMPLETE   ${NC}"
    echo -e "${GREEN}=========================================${NC}\n"
    
    echo -e "Access your services at:\n"
    echo -e "  ${BLUE}Home Assistant:${NC}  http://localhost:8123"
    echo -e "  ${BLUE}n8n:${NC}             http://localhost:5678"
    echo -e "  ${BLUE}Open WebUI:${NC}      http://localhost:3000"
    echo -e "  ${BLUE}Ollama API:${NC}      http://localhost:11434\n"
    
    echo -e "${YELLOW}Next Steps:${NC}\n"
    echo "1. Open Home Assistant (http://localhost:8123) and complete initial setup"
    echo "2. Create a Long-Lived Access Token in HA and add it to docker/.env"
    echo "3. Install HACS in Home Assistant, then add 'Extended OpenAI Conversation'"
    echo "4. Open n8n (http://localhost:5678) and import workflows from n8n/workflows/"
    echo "5. Open Open WebUI (http://localhost:3000) and configure the LCARS persona"
    echo "6. Configure voice satellites (see esphome/ directory)\n"
    
    echo -e "For detailed instructions, see: ${BLUE}README.md${NC}\n"
    
    echo -e "${YELLOW}Useful Commands:${NC}\n"
    echo "  View logs:        cd $DOCKER_DIR && docker compose logs -f"
    echo "  Stop services:    cd $DOCKER_DIR && docker compose down"
    echo "  Restart services: cd $DOCKER_DIR && docker compose restart"
    echo "  Health check:     python3 $SCRIPT_DIR/health_check.py\n"
    
    if [[ "$GPU_ENABLED" == true ]]; then
        echo -e "${GREEN}GPU support is enabled.${NC} Verify with: nvidia-smi\n"
    fi
}

# Main execution
main() {
    echo -e "\n${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║         LCARS COMPUTER - AUTOMATED DEPLOYMENT                ║"
    echo "║         Star Trek Voice Assistant for Home Automation        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    # Initialize log file
    echo "=== LCARS Deployment Log - $(date) ===" > "$LOG_FILE"
    
    # Run deployment steps
    check_requirements
    install_docker
    install_nvidia_toolkit
    setup_directories
    setup_environment
    setup_homeassistant_config
    configure_gpu_support
    start_services
    setup_ollama_model
    print_instructions
    
    log INFO "Deployment log saved to: $LOG_FILE"
}

# Run the script
main "$@"
