.PHONY: demo-video ingest test lint format api web up

ingest:
	cd backend && python -m app.ingest.snapshot

test:
	cd backend && python -m pytest

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint && npm run format:check

format:
	cd backend && ruff check --fix . && ruff format .
	cd frontend && npm run format

api:
	cd backend && uvicorn app.main:app --reload

web:
	cd frontend && npm run dev

up:
	docker compose up --build

# Records the screen-only demo video to demo/out/ (add your voiceover afterwards).
demo-video:
	demo/run.sh
