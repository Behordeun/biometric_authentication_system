## Quick orientation for AI code assistants

This repository implements a hybrid passwordless authentication system (FastAPI backend + React frontend) with Docker, Kubernetes and Terraform artifacts. Use the guidance below to produce code, tests, and fixes that match repository conventions.

High-level pointers
- Backend lives in `backend/` (FastAPI app under `backend/app/`). Frontend in `frontend/`.
- Primary workflows are docker-first. See `Makefile` and `docker/docker-start.sh`. Typical commands: `make docker-up`, `./docker/docker-start.sh`.
- Local development often runs `uvicorn app.main:app --reload` from `backend/` or `make dev`.

What to change and where
- HTTP endpoints and business logic: `backend/app/api/routes/` and `backend/app/services/`.
- DB models and migrations: `backend/app/db/` and `database/init.sql` / `backend/migrations/` (alembic).
- Configuration: `backend/.env.example` — runtime uses `backend/.env` (Docker symlinks to `docker/.env`).

Tests & quality gates
- Backend tests: `backend/tests/` — run via `make test` or `cd backend && pytest`.
- Coverage and quality: repository expects high coverage; CI runs pytest with `--cov` and mypy. Follow `pyproject.toml` and `Makefile` targets for exact flags.
- Formatting: `black` + `isort`. Run `make format` or `cd backend && black app/`.

Conventions and idioms to preserve
- Type-first Python (3.11+). Many modules are mypy-strict — add type annotations for public functions and return values.
- Structured, security-aware logging and careful secret handling. Avoid printing secrets; use `scripts/generate-secrets.sh` and `.env`.
- Lazy-load heavy ML/AI models (see `voice_transcription_and_translation/voice_translation/core/processor.py` for patterns: initialize once, lazy-load translation/diarization models and cache them).

Integration points and external dependencies
- PostgreSQL (see `database/` and `init.sql`) — migrations performed with Alembic in `backend/`.
- Redis (cache) and other services spun up by `docker/docker-compose.yml` used by `make docker-up`.
- Hugging Face / Whisper / transformers are used in `voice_transcription_and_translation/` — if touching ML code, replicate patterns: guard token access via `HUGGINGFACE_TOKEN` env var and wrap external model loads in try/except logging.

When writing code changes
- Keep small, self-contained PRs that: add unit tests under `backend/tests/` or `voice_transcription_and_translation/tests/`; run `pytest` locally; include type hints; update docs in `docs/` if behavior changes.
- Preserve API contracts for routes under `backend/app/api/routes/`. If you must change request/response shapes, update OpenAPI docs (FastAPI auto-generates from type hints) and note it in PR description.

Examples to reference when implementing changes
- Use `backend/app/core/*` for common utilities (config, logging, auth helpers).
- Database session usage patterns appear in `backend/app/db/*` — use async sessions the same way.
- For multi-file features, mirror the structure: route -> service -> db model -> tests.

Quick checks before submitting code
- Run `make lint` / `make format` and `make test` (or at least `cd backend && pytest -q`).
- Ensure no secrets in diffs (.env or terraform.tfvars).
- Add or update `docs/` when introducing new developer-visible behavior or commands.

If anything is unclear
- Ask for the intended runtime: Docker compose vs local venv. Mention relevant files (e.g., `Makefile`, `docker/docker-start.sh`, `backend/.env.example`) so the maintainers can confirm.

End of instructions.
