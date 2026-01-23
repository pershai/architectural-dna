#!/bin/bash
# Safe Docker Compose wrapper that prevents accidental data loss
# Usage: ./scripts/docker-safe.sh [command]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get Qdrant point count
get_point_count() {
    curl -s http://localhost:6333/collections/code_dna 2>/dev/null | \
        grep -o '"points_count":[0-9]*' | \
        grep -o '[0-9]*' || echo "0"
}

case "$1" in
    up)
        echo -e "${GREEN}Starting services...${NC}"
        docker compose up -d "${@:2}"
        ;;

    down)
        # Check if -v flag is present
        if [[ " $* " =~ " -v " ]] || [[ " $* " =~ " --volumes " ]]; then
            POINTS=$(get_point_count)
            if [ "$POINTS" -gt 0 ]; then
                echo -e "${RED}WARNING: You are about to remove volumes!${NC}"
                echo -e "${YELLOW}Qdrant contains $POINTS patterns that will be PERMANENTLY DELETED.${NC}"
                echo ""
                read -p "Are you sure? Type 'DELETE' to confirm: " confirm
                if [ "$confirm" != "DELETE" ]; then
                    echo -e "${GREEN}Aborted. Your data is safe.${NC}"
                    exit 1
                fi
                echo -e "${YELLOW}Creating backup before deletion...${NC}"
                $0 backup
            fi
        fi
        docker compose down "${@:2}"
        ;;

    restart)
        echo -e "${GREEN}Restarting services (data preserved)...${NC}"
        docker compose restart "${@:2}"
        ;;

    rebuild)
        echo -e "${GREEN}Rebuilding without removing data...${NC}"
        docker compose build "${@:2}"
        docker compose up -d "${@:2}"
        ;;

    backup)
        BACKUP_DIR="$PROJECT_DIR/backups"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="$BACKUP_DIR/qdrant_backup_$TIMESTAMP.tar.gz"

        mkdir -p "$BACKUP_DIR"

        POINTS=$(get_point_count)
        echo -e "${GREEN}Backing up Qdrant data ($POINTS patterns)...${NC}"

        # Create snapshot via Qdrant API
        SNAPSHOT_NAME=$(curl -s -X POST "http://localhost:6333/collections/code_dna/snapshots" | \
            grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -n "$SNAPSHOT_NAME" ]; then
            # Download snapshot
            curl -s "http://localhost:6333/collections/code_dna/snapshots/$SNAPSHOT_NAME" \
                -o "$BACKUP_FILE"
            echo -e "${GREEN}Backup saved to: $BACKUP_FILE${NC}"

            # Clean up snapshot from Qdrant
            curl -s -X DELETE "http://localhost:6333/collections/code_dna/snapshots/$SNAPSHOT_NAME" > /dev/null
        else
            echo -e "${YELLOW}No data to backup or backup failed${NC}"
        fi
        ;;

    restore)
        if [ -z "$2" ]; then
            echo "Usage: $0 restore <backup_file>"
            echo "Available backups:"
            ls -la "$PROJECT_DIR/backups/"*.tar.gz 2>/dev/null || echo "  No backups found"
            exit 1
        fi

        BACKUP_FILE="$2"
        if [ ! -f "$BACKUP_FILE" ]; then
            echo -e "${RED}Backup file not found: $BACKUP_FILE${NC}"
            exit 1
        fi

        echo -e "${YELLOW}Restoring from: $BACKUP_FILE${NC}"
        curl -X POST "http://localhost:6333/collections/code_dna/snapshots/upload" \
            -H "Content-Type: multipart/form-data" \
            -F "snapshot=@$BACKUP_FILE"
        echo -e "${GREEN}Restore complete!${NC}"
        ;;

    status)
        echo -e "${GREEN}=== Docker Status ===${NC}"
        docker compose ps
        echo ""
        echo -e "${GREEN}=== Qdrant Stats ===${NC}"
        POINTS=$(get_point_count)
        echo "Patterns stored: $POINTS"
        ;;

    *)
        echo "Safe Docker Compose wrapper for Architectural DNA"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  up [args]      - Start services"
        echo "  down [args]    - Stop services (warns before removing volumes)"
        echo "  restart        - Restart services (preserves data)"
        echo "  rebuild        - Rebuild and restart (preserves data)"
        echo "  backup         - Create Qdrant snapshot backup"
        echo "  restore <file> - Restore from backup"
        echo "  status         - Show status and pattern count"
        echo ""
        echo "Examples:"
        echo "  $0 up -d"
        echo "  $0 down           # Safe - keeps data"
        echo "  $0 down -v        # Warns and requires confirmation"
        echo "  $0 backup"
        ;;
esac
