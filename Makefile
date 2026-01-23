# Makefile for Architectural DNA Docker operations

.PHONY: help build up down logs restart clean shell qdrant-shell test migrate backup restore stats

# Default target
help:
	@echo "Architectural DNA - Docker Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initial setup (copy .env file)"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo ""
	@echo "Operations:"
	@echo "  make logs           - View application logs"
	@echo "  make logs-qdrant    - View Qdrant logs"
	@echo "  make restart        - Restart services"
	@echo "  make status         - Show service status"
	@echo ""
	@echo "Development:"
	@echo "  make shell          - Open shell in dna-server container"
	@echo "  make qdrant-shell   - Open shell in Qdrant container"
	@echo "  make test           - Run tests in container"
	@echo "  make migrate        - Run collection migration"
	@echo ""
	@echo "Data Management:"
	@echo "  make stats          - Show Qdrant collection stats"
	@echo "  make backup         - Create Qdrant snapshot backup"
	@echo "  make restore        - Restore from backup file"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Stop and remove containers"
	@echo "  make clean-volumes  - Remove volumes (SAFE: requires 'DELETE' confirmation)"
	@echo "  make rebuild        - Clean rebuild of all services"
	@echo ""

# Setup
setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example template..."; \
		cp .env.example .env; \
		echo "✓ Created .env file"; \
		echo "⚠️  Please edit .env and add your API keys"; \
		echo "⚠️  For Docker: uncomment QDRANT_URL=http://qdrant:6333"; \
	else \
		echo ".env file already exists"; \
	fi

# Build
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo ""
	@echo "Services started!"
	@echo "  • Qdrant: http://localhost:6333"
	@echo "  • Qdrant Dashboard: http://localhost:6333/dashboard"
	@echo ""
	@echo "View logs with: make logs"

# Start with logs
up-logs:
	docker-compose up

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f dna-server

logs-qdrant:
	docker-compose logs -f qdrant

logs-all:
	docker-compose logs -f

# Restart services
restart:
	docker-compose restart

# Service status
status:
	docker-compose ps

# Open shell in application container
shell:
	docker-compose exec dna-server /bin/bash

# Open shell in Qdrant container
qdrant-shell:
	docker-compose exec qdrant /bin/sh

# Run tests
test:
	docker-compose exec dna-server python test_embeddings.py

test-mcp:
	docker-compose exec dna-server python test_mcp_tools.py

# Run collection migration
migrate:
	docker-compose exec dna-server python migrate_collection.py

# Clean up
clean:
	docker-compose down --remove-orphans

clean-volumes:
	@echo "⚠️  WARNING: This will PERMANENTLY DELETE all data!"
	@echo ""
	@POINTS=$$(curl -s http://localhost:6333/collections/code_dna 2>/dev/null | \
		python -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "unknown"); \
	echo "📊 Current patterns in Qdrant: $$POINTS"; \
	echo ""; \
	read -p "Type 'DELETE' to confirm removal: " confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		echo "Creating backup first..."; \
		$(MAKE) backup || true; \
		docker-compose down -v --remove-orphans; \
		echo "✓ Volumes removed"; \
	else \
		echo "❌ Cancelled - data preserved"; \
	fi

# Backup Qdrant data
backup:
	@mkdir -p backups
	@echo "Creating Qdrant snapshot..."
	@SNAPSHOT=$$(curl -s -X POST "http://localhost:6333/collections/code_dna/snapshots" 2>/dev/null | \
		python -c "import sys,json; print(json.load(sys.stdin)['result']['name'])" 2>/dev/null) && \
	if [ -n "$$SNAPSHOT" ]; then \
		TIMESTAMP=$$(date +%Y%m%d_%H%M%S) && \
		curl -s "http://localhost:6333/collections/code_dna/snapshots/$$SNAPSHOT" \
			-o "backups/qdrant_$$TIMESTAMP.snapshot" && \
		curl -s -X DELETE "http://localhost:6333/collections/code_dna/snapshots/$$SNAPSHOT" > /dev/null && \
		echo "✓ Backup saved: backups/qdrant_$$TIMESTAMP.snapshot"; \
	else \
		echo "⚠️  No data to backup or Qdrant not running"; \
	fi

# Restore from backup
restore:
	@echo "Available backups:"
	@ls -1 backups/*.snapshot 2>/dev/null || echo "  No backups found"
	@echo ""
	@read -p "Enter backup filename (or path): " file; \
	if [ -f "$$file" ]; then \
		curl -X POST "http://localhost:6333/collections/code_dna/snapshots/upload" \
			-H "Content-Type: multipart/form-data" \
			-F "snapshot=@$$file" && \
		echo "✓ Restore complete"; \
	else \
		echo "❌ File not found: $$file"; \
	fi

# Show Qdrant stats
stats:
	@echo "=== Qdrant Collection Stats ==="
	@curl -s http://localhost:6333/collections/code_dna 2>/dev/null | \
		python -c "import sys,json; d=json.load(sys.stdin)['result']; print(f\"Status: {d['status']}\nPoints: {d['points_count']}\nVectors: {d['indexed_vectors_count']}\")" \
		|| echo "Qdrant not running or collection doesn't exist"

# Rebuild everything
rebuild: clean
	docker-compose build --no-cache
	docker-compose up -d

# Quick start (setup + build + up)
quickstart: setup build up
	@echo ""
	@echo "✓ Architectural DNA is running!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your API keys"
	@echo "  2. Run 'make restart' to apply changes"
	@echo "  3. Run 'make test' to verify setup"
