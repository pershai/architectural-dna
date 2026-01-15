# Makefile for Architectural DNA Docker operations

.PHONY: help build up down logs restart clean shell qdrant-shell test migrate

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
	@echo "Maintenance:"
	@echo "  make clean          - Stop and remove containers"
	@echo "  make clean-volumes  - Remove volumes (WARNING: deletes data)"
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
	@echo "⚠️  WARNING: This will delete all data including patterns and embeddings!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --remove-orphans; \
		echo "✓ Volumes removed"; \
	else \
		echo "Cancelled"; \
	fi

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
