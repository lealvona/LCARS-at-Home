#!/usr/bin/env bash
#
# LCARS Computer - System Update Script
#
# This script updates all Docker containers in the LCARS Computer stack to their
# latest versions. It includes safeguards like automatic backups, health checks,
# and rollback capabilities to ensure safe updates.
#
# OS notes:
#   - Primary target: Linux Mint Xia (Ubuntu-based) / Ubuntu / Debian using Docker Engine.
#   - Windows/macOS: Use Docker Desktop; run the same compose commands, but note host networking differs.
#     See docs/DOCKER_INSTALL.md and docker/docker-compose.desktop.yml.
#
# The update process follows these steps:
#   1. Create a backup of current configuration
#   2. Pull new Docker images
#   3. Gracefully stop services
#   4. Start services with new images
#   5. Verify health of all services
#   6. Report status and any issues
#
# Usage:
#   ./update.sh [options]
#
# Options:
#   --no-backup     Skip automatic backup before update
#   --service NAME  Update only a specific service
#   --dry-run       Show what would be updated without making changes
#   --force         Continue even if health checks fail
#   --help          Show this help message

set -euo pipefail

# Script configuration variables. These paths are relative to the script location
# and can be overridden by environment variables if needed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_DIR/docker"
LOG_FILE="$PROJECT_DIR/update.log"

# Color codes provide visual feedback in the terminal, making it easier to
# quickly identify success, warnings, and errors at a glance.
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default option values. These can be modified by command-line arguments.
SKIP_BACKUP=false
SINGLE_SERVICE=""
DRY_RUN=false
FORCE_UPDATE=false

# Parse command-line arguments using a while loop with a case statement.
# This approach handles both short and long option formats cleanly.
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --service)
            SINGLE_SERVICE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE_UPDATE=true
            shift
            ;;
        --help)
            head -35 "$0" | tail -30
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Logging function that writes timestamped messages to both the console and
# a log file. This creates an audit trail of all update activities.
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

# Check that Docker is running before attempting any operations. Docker being
# unavailable would cause all subsequent commands to fail mysteriously.
check_docker() {
    if ! docker info &> /dev/null; then
        log ERROR "Docker is not running or not accessible."
        log INFO "Please start Docker and try again."
        exit 1
    fi
}

# Create a backup before updating to enable rollback if something goes wrong.
# This uses the backup.py script to create a timestamped snapshot.
create_backup() {
    if [[ "$SKIP_BACKUP" == true ]]; then
        log WARN "Skipping backup as requested."
        return 0
    fi
    
    log STEP "Creating Pre-Update Backup"
    
    if [[ -f "$SCRIPT_DIR/backup.py" ]]; then
        python3 "$SCRIPT_DIR/backup.py" --compress --output "$PROJECT_DIR/backups" --keep 5
        log INFO "Backup created successfully."
    else
        log WARN "Backup script not found. Proceeding without backup."
    fi
}

# Get the currently running image digest for a container. This allows us to
# detect whether a new image is actually different from what's running.
get_current_digest() {
    local container_id="$1"
    docker inspect --format='{{.Image}}' "$container_id" 2>/dev/null || echo "none"
}

# Resolve a compose service name to a container ID.
get_service_container_id() {
    local service="$1"
    cd "$DOCKER_DIR"
    docker compose ps -q "$service" 2>/dev/null | head -n 1
}

# Check for available updates by comparing the currently running image digest
# with the digest of the latest available image from the registry.
check_for_updates() {
    log STEP "Checking for Available Updates"
    
    cd "$DOCKER_DIR"
    
    # Get list of services from docker-compose. The awk command extracts just
    # the service names, which we'll iterate through to check for updates.
    local services
    if [[ -n "$SINGLE_SERVICE" ]]; then
        services="$SINGLE_SERVICE"
    else
        services=$(docker compose config --services 2>/dev/null)
    fi
    
    local updates_available=false
    
    for service in $services; do
        # Get the image name from docker-compose config
        local image=$(docker compose config | grep -A 5 "^  $service:" | grep "image:" | awk '{print $2}')
        
        if [[ -z "$image" ]]; then
            continue
        fi
        
        log INFO "Checking $service ($image)..."
        
        # Pull the image to check for updates (this downloads the manifest first)
        if docker pull "$image" --quiet &> /dev/null; then
            # Compare digests to determine if there's an actual update
            local container_id=$(get_service_container_id "$service")
            local running_digest="none"
            if [[ -n "$container_id" ]]; then
                running_digest=$(get_current_digest "$container_id" 2>/dev/null || echo "none")
            fi
            local latest_digest=$(docker inspect --format='{{.Id}}' "$image" 2>/dev/null || echo "unknown")
            
            if [[ "$running_digest" != "$latest_digest" ]]; then
                log INFO "  ${GREEN}Update available${NC} for $service"
                updates_available=true
            else
                log INFO "  Already up to date"
            fi
        else
            log WARN "  Could not check for updates"
        fi
    done
    
    if [[ "$updates_available" == false ]]; then
        log INFO "All services are up to date."
        if [[ "$FORCE_UPDATE" != true ]]; then
            log INFO "No updates to apply. Use --force to restart services anyway."
            return 1
        fi
    fi
    
    return 0
}

# Pull all new images before stopping services. This minimizes downtime by
# ensuring all images are ready before we begin the actual update process.
pull_images() {
    log STEP "Pulling Latest Images"
    
    cd "$DOCKER_DIR"
    
    if [[ "$DRY_RUN" == true ]]; then
        log INFO "[DRY RUN] Would pull images for all services"
        return 0
    fi
    
    # Determine which compose files to use based on GPU configuration
    local compose_cmd="docker compose"
    if [[ -f "$DOCKER_DIR/docker-compose.gpu.yml" ]] && nvidia-smi &> /dev/null; then
        compose_cmd="docker compose -f docker-compose.yml -f docker-compose.gpu.yml"
    fi
    
    if [[ -n "$SINGLE_SERVICE" ]]; then
        $compose_cmd pull "$SINGLE_SERVICE"
    else
        $compose_cmd pull
    fi
    
    log INFO "All images pulled successfully."
}

# Gracefully stop services to allow them to clean up properly. We use a timeout
# to prevent hanging services from blocking the update indefinitely.
stop_services() {
    log STEP "Stopping Services"
    
    cd "$DOCKER_DIR"
    
    if [[ "$DRY_RUN" == true ]]; then
        log INFO "[DRY RUN] Would stop services"
        return 0
    fi
    
    local compose_cmd="docker compose"
    if [[ -f "$DOCKER_DIR/docker-compose.gpu.yml" ]] && nvidia-smi &> /dev/null; then
        compose_cmd="docker compose -f docker-compose.yml -f docker-compose.gpu.yml"
    fi
    
    if [[ -n "$SINGLE_SERVICE" ]]; then
        $compose_cmd stop "$SINGLE_SERVICE"
    else
        # Stop services in reverse dependency order to prevent issues
        $compose_cmd stop --timeout 30
    fi
    
    log INFO "Services stopped."
}

# Start services with the new images. Docker Compose will automatically use
# the newly pulled images when recreating the containers.
start_services() {
    log STEP "Starting Services with New Images"
    
    cd "$DOCKER_DIR"
    
    if [[ "$DRY_RUN" == true ]]; then
        log INFO "[DRY RUN] Would start services"
        return 0
    fi
    
    local compose_cmd="docker compose"
    if [[ -f "$DOCKER_DIR/docker-compose.gpu.yml" ]] && nvidia-smi &> /dev/null; then
        compose_cmd="docker compose -f docker-compose.yml -f docker-compose.gpu.yml"
    fi
    
    if [[ -n "$SINGLE_SERVICE" ]]; then
        $compose_cmd up -d "$SINGLE_SERVICE"
    else
        $compose_cmd up -d
    fi
    
    log INFO "Services started. Waiting for initialization..."
    sleep 15
}

# Verify that all services are healthy after the update. This catches issues
# early before they impact users of the system.
verify_health() {
    log STEP "Verifying Service Health"
    
    if [[ "$DRY_RUN" == true ]]; then
        log INFO "[DRY RUN] Would verify service health"
        return 0
    fi
    
    local all_healthy=true
    local max_wait=60
    local wait_interval=5
    local waited=0
    
    # Wait for services to become healthy, checking periodically
    while [[ $waited -lt $max_wait ]]; do
        all_healthy=true
        
        # Check each service's health. We look for containers that are running
        # and have passed their health checks if one is defined.
        cd "$DOCKER_DIR"
        
        local services
        if [[ -n "$SINGLE_SERVICE" ]]; then
            services="$SINGLE_SERVICE"
        else
            services=$(docker compose config --services 2>/dev/null)
        fi
        
        for service in $services; do
            local container_id=$(get_service_container_id "$service")
            local status="not_found"
            if [[ -n "$container_id" ]]; then
                status=$(docker inspect --format='{{.State.Status}}' "$container_id" 2>/dev/null || echo "not_found")
            fi
            
            if [[ "$status" != "running" ]]; then
                all_healthy=false
                break
            fi
        done
        
        if [[ "$all_healthy" == true ]]; then
            break
        fi
        
        sleep $wait_interval
        waited=$((waited + wait_interval))
    done
    
    # Run the health check script if available for more detailed verification
    if [[ -f "$SCRIPT_DIR/health_check.py" ]]; then
        log INFO "Running detailed health check..."
        if python3 "$SCRIPT_DIR/health_check.py"; then
            log INFO "All health checks passed."
            return 0
        else
            log WARN "Some health checks failed."
            if [[ "$FORCE_UPDATE" != true ]]; then
                return 1
            fi
        fi
    fi
    
    if [[ "$all_healthy" == true ]]; then
        log INFO "All services are running."
        return 0
    else
        log ERROR "Some services failed to start properly."
        return 1
    fi
}

# Clean up old Docker images that are no longer in use. This recovers disk
# space that accumulates over time as images are updated.
cleanup_images() {
    log STEP "Cleaning Up Old Images"
    
    if [[ "$DRY_RUN" == true ]]; then
        log INFO "[DRY RUN] Would clean up old images"
        return 0
    fi
    
    # Remove dangling images (those with <none> tags) that are left behind
    # when new images replace old ones
    local space_before=$(docker system df --format '{{.Size}}' | head -1)
    
    docker image prune -f
    
    local space_after=$(docker system df --format '{{.Size}}' | head -1)
    
    log INFO "Cleanup complete. Space recovered: $space_before -> $space_after"
}

# Display a summary of what was updated and the final system status.
print_summary() {
    log STEP "Update Complete"
    
    echo -e "\n${GREEN}=========================================${NC}"
    echo -e "${GREEN}      LCARS COMPUTER UPDATE SUMMARY      ${NC}"
    echo -e "${GREEN}=========================================${NC}\n"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}This was a dry run. No changes were made.${NC}\n"
    fi
    
    cd "$DOCKER_DIR"
    docker compose ps
    
    echo -e "\n${BLUE}Useful Commands:${NC}"
    echo "  View logs:       docker compose logs -f"
    echo "  Service status:  docker compose ps"
    echo "  Health check:    python3 $SCRIPT_DIR/health_check.py"
    
    echo -e "\n${BLUE}If issues occur:${NC}"
    echo "  Rollback:        docker compose down && docker compose up -d"
    echo "  Restore backup:  See backups/ directory"
    echo ""
}

# Main execution function that orchestrates all update steps in the proper
# order, handling errors and providing appropriate feedback.
main() {
    echo -e "\n${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           LCARS COMPUTER - SYSTEM UPDATE UTILITY             ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    # Initialize the log file for this update session
    echo "=== LCARS Update Log - $(date) ===" >> "$LOG_FILE"
    
    # Verify Docker is available before proceeding
    check_docker
    
    # Create a backup unless explicitly skipped
    create_backup
    
    # Check for and apply updates
    if check_for_updates || [[ "$FORCE_UPDATE" == true ]]; then
        pull_images
        stop_services
        start_services
        
        if verify_health; then
            cleanup_images
            print_summary
            log INFO "Update completed successfully."
        else
            log ERROR "Update completed with warnings. Some services may not be healthy."
            if [[ "$FORCE_UPDATE" != true ]]; then
                log INFO "Consider rolling back to the previous version."
                exit 1
            fi
        fi
    else
        log INFO "No updates needed."
    fi
    
    log INFO "Update log saved to: $LOG_FILE"
}

# Execute the main function with all command-line arguments
main "$@"
