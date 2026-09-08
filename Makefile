# NyayaLens — Makefile
# Usage:
#   make dev        → start FastAPI backend + Next.js frontend concurrently
#   make backend    → start FastAPI only
#   make frontend   → start Next.js only
#   make install    → install all backend + frontend deps
#   make seed       → seed ChromaDB corpus (requires GOOGLE_API_KEY in .env)
#   make check      → syntax check all backend Python files
#   make clean      → remove build artifacts

SHELL := /bin/bash
BACKEND_DIR := ./backend
FRONTEND_DIR := ./web

# Colours for terminal output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

.PHONY: dev backend frontend install seed check clean help

## ─── Default target ──────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  $(CYAN)NyayaLens — Legal Voice AI$(RESET)"
	@echo ""
	@echo "  $(GREEN)make dev$(RESET)       → Start FastAPI + Next.js concurrently"
	@echo "  $(GREEN)make backend$(RESET)   → Start FastAPI server only   (port 8000)"
	@echo "  $(GREEN)make frontend$(RESET)  → Start Next.js dev server    (port 3000)"
	@echo "  $(GREEN)make install$(RESET)   → Install all deps (Python + npm)"
	@echo "  $(GREEN)make seed$(RESET)      → Seed ChromaDB corpus (needs GOOGLE_API_KEY)"
	@echo "  $(GREEN)make check$(RESET)     → Syntax check all backend .py files"
	@echo "  $(GREEN)make clean$(RESET)     → Remove build artifacts"
	@echo ""

## ─── dev: run backend + frontend together ────────────────────────────────────
dev:
	@echo "$(GREEN)▶ Starting NyayaLens — Backend + Frontend$(RESET)"
	@trap 'kill 0' INT; \
	( \
	  cd $(BACKEND_DIR) && \
	  echo "$(CYAN)[backend]$(RESET) FastAPI → http://localhost:8000" && \
	  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | sed 's/^/[backend] /' \
	) & \
	( \
	  cd $(FRONTEND_DIR) && \
	  echo "$(CYAN)[frontend]$(RESET) Next.js  → http://localhost:3000" && \
	  npm run dev 2>&1 | sed 's/^/[frontend] /' \
	) & \
	wait

## ─── backend: FastAPI only ───────────────────────────────────────────────────
backend:
	@echo "$(GREEN)▶ Starting FastAPI backend on :8000$(RESET)"
	cd $(BACKEND_DIR) && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

## ─── frontend: Next.js only ──────────────────────────────────────────────────
frontend:
	@echo "$(GREEN)▶ Starting Next.js frontend on :3000$(RESET)"
	cd $(FRONTEND_DIR) && npm run dev

## ─── install: Python deps + npm deps ────────────────────────────────────────
install:
	@echo "$(YELLOW)▶ Installing Python dependencies…$(RESET)"
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	@echo "$(YELLOW)▶ Installing Node.js dependencies…$(RESET)"
	cd $(FRONTEND_DIR) && npm install
	@echo "$(GREEN)✅ All dependencies installed.$(RESET)"


## ─── check: AST syntax check all backend Python files ───────────────────────
check:
	@python3 -c "import pathlib, py_compile; files = list(pathlib.Path('$(BACKEND_DIR)/app').rglob('*.py')); [py_compile.compile(str(f), doraise=True) for f in files]; print(f'✅ {len(files)} .py files syntax clean')"
	@echo "$(GREEN)✅ Check complete.$(RESET)"

## ─── clean: remove build artefacts ──────────────────────────────────────────
clean:
	@echo "$(YELLOW)▶ Cleaning build artifacts…$(RESET)"
	rm -rf $(FRONTEND_DIR)/.next $(FRONTEND_DIR)/out
	find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Clean complete.$(RESET)"
