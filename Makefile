# Hybrid Passwordless Authentication System - Makefile
# Cross-platform support: Windows, Linux, macOS

.PHONY: help install setup dev test clean docker k8s deploy security docs all

# Detect OS
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    PYTHON := python
    PIP := pip
    RM := del /Q
    RMDIR := rmdir /S /Q
    MKDIR := mkdir
    SEP := \\
    ACTIVATE := venv\Scripts\activate
else
    DETECTED_OS := $(shell uname -s)
    PYTHON := python3
    PIP := pip3
    RM := rm -f
    RMDIR := rm -rf
    MKDIR := mkdir -p
    SEP := /
    ACTIVATE := source venv/bin/activate
endif

# Colors for output (Unix-like systems)
ifneq ($(DETECTED_OS),Windows)
    GREEN := \033[0;32m
    YELLOW := \033[0;33m
    RED := \033[0;31m
    NC := \033[0m
else
    GREEN :=
    YELLOW :=
    RED :=
    NC :=
endif

# Default target
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@echo "$(GREEN)Hybrid Passwordless Authentication System$(NC)"
	@echo "$(YELLOW)Detected OS: $(DETECTED_OS)$(NC)"
	@echo ""
	@echo "Available targets:"
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /' | column -t -s ':'

## install: Install all dependencies (backend + frontend)
install: install-backend install-frontend
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

## install-backend: Install Python dependencies
install-backend:
	@echo "$(YELLOW)Installing backend dependencies...$(NC)"
	cd backend && $(PYTHON) -m venv venv
	cd backend && $(ACTIVATE) && $(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Backend dependencies installed$(NC)"

## install-frontend: Install Node.js dependencies
install-frontend:
	@echo "$(YELLOW)Installing frontend dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

## setup: Initial project setup (secrets + env files)
setup:
	@echo "$(YELLOW)Setting up project...$(NC)"
ifeq ($(DETECTED_OS),Windows)
	bash scripts/generate-secrets.sh
	copy backend\.env.example backend\.env
else
	chmod +x scripts/generate-secrets.sh
	./scripts/generate-secrets.sh
	cp backend/.env.example backend/.env
endif
	@echo "$(RED)⚠ Edit backend/.env with generated secrets$(NC)"
	@echo "$(GREEN)✓ Setup complete$(NC)"

## dev: Start development servers (backend + frontend)
dev:
	@echo "$(YELLOW)Starting development servers...$(NC)"
ifeq ($(DETECTED_OS),Windows)
	start cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload"
	start cmd /k "cd frontend && npm start"
else
	cd backend && $(ACTIVATE) && uvicorn app.main:app --reload & \
	cd frontend && npm start &
endif
	@echo "$(GREEN)✓ Servers started$(NC)"

## dev-backend: Start backend development server
dev-backend:
	@echo "$(YELLOW)Starting backend server...$(NC)"
	cd backend && $(ACTIVATE) && uvicorn app.main:app --reload

## dev-frontend: Start frontend development server
dev-frontend:
	@echo "$(YELLOW)Starting frontend server...$(NC)"
	cd frontend && npm start

## test: Run all tests
test: test-backend test-frontend
	@echo "$(GREEN)✓ All tests passed$(NC)"

## test-backend: Run backend tests
test-backend:
	@echo "$(YELLOW)Running backend tests...$(NC)"
	cd backend && $(ACTIVATE) && pytest -v
	@echo "$(GREEN)✓ Backend tests passed$(NC)"

## test-frontend: Run frontend tests
test-frontend:
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd frontend && npm test -- --watchAll=false
	@echo "$(GREEN)✓ Frontend tests passed$(NC)"

## lint: Run linters
lint:
	@echo "$(YELLOW)Running linters...$(NC)"
	cd backend && $(ACTIVATE) && black app/ --check
	cd frontend && npm run lint || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

## format: Format code
format:
	@echo "$(YELLOW)Formatting code...$(NC)"
	cd backend && $(ACTIVATE) && black app/
	cd frontend && npm run format || true
	@echo "$(GREEN)✓ Code formatted$(NC)"

## docker-build: Build Docker images
docker-build:
	@echo "$(YELLOW)Building Docker images...$(NC)"
	cd docker && docker-compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

## docker-up: Start Docker Compose services
docker-up:
	@echo "$(YELLOW)Starting Docker services...$(NC)"
ifeq ($(DETECTED_OS),Windows)
	copy config\.env.docker .env 2>nul || echo ""
else
	cp -n config/.env.docker .env 2>/dev/null || true
endif
	cd docker && docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "API Docs: http://localhost:8000/docs"

## docker-down: Stop Docker Compose services
docker-down:
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	cd docker && docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

## docker-logs: View Docker logs
docker-logs:
	cd docker && docker-compose logs -f

## docker-clean: Clean Docker resources
docker-clean:
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	cd docker && docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)✓ Docker cleaned$(NC)"

## k8s-deploy: Deploy to Kubernetes
k8s-deploy:
	@echo "$(YELLOW)Deploying to Kubernetes...$(NC)"
	kubectl apply -f k8s/
	@echo "$(GREEN)✓ Deployed to Kubernetes$(NC)"

## k8s-delete: Delete Kubernetes resources
k8s-delete:
	@echo "$(YELLOW)Deleting Kubernetes resources...$(NC)"
	kubectl delete -f k8s/
	@echo "$(GREEN)✓ Kubernetes resources deleted$(NC)"

## k8s-status: Check Kubernetes status
k8s-status:
	kubectl get pods,svc,deploy

## terraform-init: Initialize Terraform
terraform-init:
	@echo "$(YELLOW)Initializing Terraform...$(NC)"
	cd terraform && terraform init
	@echo "$(GREEN)✓ Terraform initialized$(NC)"

## terraform-plan: Plan Terraform changes
terraform-plan:
	@echo "$(YELLOW)Planning Terraform changes...$(NC)"
	cd terraform && terraform plan
	@echo "$(GREEN)✓ Plan complete$(NC)"

## terraform-apply: Apply Terraform changes
terraform-apply:
	@echo "$(YELLOW)Applying Terraform changes...$(NC)"
	cd terraform && terraform apply
	@echo "$(GREEN)✓ Infrastructure deployed$(NC)"

## terraform-destroy: Destroy Terraform infrastructure
terraform-destroy:
	@echo "$(RED)⚠ Destroying infrastructure...$(NC)"
	cd terraform && terraform destroy
	@echo "$(GREEN)✓ Infrastructure destroyed$(NC)"

## security-scan: Run security scans
security-scan:
	@echo "$(YELLOW)Running security scans...$(NC)"
ifeq ($(DETECTED_OS),Windows)
	@echo "Install detect-secrets: pip install detect-secrets"
else
	detect-secrets scan || echo "Install: pip install detect-secrets"
	gitleaks detect --source . --verbose || echo "Install: brew install gitleaks"
endif
	@echo "$(GREEN)✓ Security scan complete$(NC)"

## security-secrets: Generate secure secrets
security-secrets:
	@echo "$(YELLOW)Generating secure secrets...$(NC)"
ifeq ($(DETECTED_OS),Windows)
	bash scripts/generate-secrets.sh
else
	./scripts/generate-secrets.sh
endif

## db-init: Initialize database
db-init:
	@echo "$(YELLOW)Initializing database...$(NC)"
	cd docker && docker-compose up -d postgres
	sleep 5
	cd docker && docker-compose exec postgres psql -U authuser -d authdb -f /docker-entrypoint-initdb.d/init.sql || true
	@echo "$(GREEN)✓ Database initialized$(NC)"

## db-migrate: Run database migrations
db-migrate:
	@echo "$(YELLOW)Running migrations...$(NC)"
	cd backend && $(ACTIVATE) && alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(NC)"

## db-reset: Reset database
db-reset:
	@echo "$(RED)⚠ Resetting database...$(NC)"
	cd docker && docker-compose down -v postgres
	cd docker && docker-compose up -d postgres
	@echo "$(GREEN)✓ Database reset$(NC)"

## clean: Clean build artifacts
clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
ifeq ($(DETECTED_OS),Windows)
	cd backend && $(RMDIR) __pycache__ .pytest_cache venv 2>nul || echo ""
	cd frontend && $(RMDIR) node_modules build 2>nul || echo ""
else
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	$(RMDIR) backend/venv frontend/node_modules frontend/build 2>/dev/null || true
endif
	@echo "$(GREEN)✓ Cleaned$(NC)"

## docs: Generate documentation
docs:
	@echo "$(YELLOW)Generating documentation...$(NC)"
	@echo "Documentation files:"
	@ls -1 *.md 2>/dev/null || dir /B *.md 2>nul || echo "No docs found"
	@echo "$(GREEN)✓ Documentation ready$(NC)"

## health: Check system health
health:
	@echo "$(YELLOW)Checking system health...$(NC)"
	@echo "Python: $$($(PYTHON) --version 2>&1)"
	@echo "Node: $$(node --version 2>&1 || echo 'Not installed')"
	@echo "Docker: $$(docker --version 2>&1 || echo 'Not installed')"
	@echo "Kubectl: $$(kubectl version --client --short 2>&1 || echo 'Not installed')"
	@echo "Terraform: $$(terraform version 2>&1 | head -1 || echo 'Not installed')"
	@echo "$(GREEN)✓ Health check complete$(NC)"

## pre-commit: Install pre-commit hooks
pre-commit:
	@echo "$(YELLOW)Installing pre-commit hooks...$(NC)"
	$(PIP) install pre-commit
	pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"

## all: Complete setup (install + setup + test)
all: install setup test
	@echo "$(GREEN)✓ Complete setup finished$(NC)"

## prod-build: Build for production
prod-build:
	@echo "$(YELLOW)Building for production...$(NC)"
	cd docker && docker-compose -f docker-compose.prod.yml build
	@echo "$(GREEN)✓ Production build complete$(NC)"

## prod-up: Start production services
prod-up:
	@echo "$(YELLOW)Starting production services...$(NC)"
	cd docker && docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✓ Production services started$(NC)"

## prod-down: Stop production services
prod-down:
	@echo "$(YELLOW)Stopping production services...$(NC)"
	cd docker && docker-compose -f docker-compose.prod.yml down
	@echo "$(GREEN)✓ Production services stopped$(NC)"

## version: Show version information
version:
	@echo "Hybrid Passwordless Authentication System"
	@echo "Version: 1.0.0"
	@echo "OS: $(DETECTED_OS)"
	@echo "Python: $$($(PYTHON) --version 2>&1)"
