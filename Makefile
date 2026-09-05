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

## ─── seed: build ChromaDB corpus ────────────────────────────────────────────
seed:
	@echo "$(YELLOW)▶ Seeding ChromaDB corpus from judgments.json…$(RESET)"
	@echo "   (Requires GOOGLE_API_KEY in $(BACKEND_DIR)/.env)"
	cd $(BACKEND_DIR) && python -m app.legal_data.corpus_builder
	@echo "$(GREEN)✅ ChromaDB corpus seeded.$(RESET)"

## ─── check: AST syntax check all backend Python files ───────────────────────
check:
	@echo "$(YELLOW)▶ Syntax-checking all backend Python files…$(RESET)"
	@python -c "\
import ast, pathlib, sys; \
errors = []; \
files = list(pathlib.Path('$(BACKEND_DIR)/app').rglob('*.py')); \
[errors.append(f'{f}: {e}') for f in files for e in [None] if not [ast.parse(f.read_text())] or False]; \
" 2>/dev/null; \
python -c "\
import ast, pathlib, sys; \
errors = []; \
files = sorted(pathlib.Path('$(BACKEND_DIR)/app').rglob('*.py')); \
[errors.append(str(f) + ': ' + str(e)) for f in files \
 for _ in [None] \
 if [setattr(sys, '_x', None)] \
 and not (lambda f: (ast.parse(f.read_text()), False)[1])(f) \
]; \
" 2>/dev/null || true; \
python -c "\
import ast, pathlib, sys; \
errors = []; \
for f in sorted(pathlib.Path('$(BACKEND_DIR)/app').rglob('*.py')): \
    try: ast.parse(f.read_text()) \
    except SyntaxError as e: errors.append(f'{f}: {e}'); \
print(f'✅ {len(list(pathlib.Path(\"$(BACKEND_DIR)/app\").rglob(\"*.py\")))} .py files syntax clean' if not errors else 'ERRORS: ' + chr(10).join(errors)); \
sys.exit(1 if errors else 0) \
"
	@echo "$(GREEN)✅ Check complete.$(RESET)"

## ─── clean: remove build artefacts ──────────────────────────────────────────
clean:
	@echo "$(YELLOW)▶ Cleaning build artifacts…$(RESET)"
	rm -rf $(FRONTEND_DIR)/.next $(FRONTEND_DIR)/out
	find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Clean complete.$(RESET)"
