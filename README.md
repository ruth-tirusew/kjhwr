# Wind Forecast Decision Portal

Pilot portal for a UK day-ahead buying team. It shows the national wind forecast that was available at the decision cutoff, how accurate those forecasts have been against actuals, and a procurement buffer in MW. Data is Elexon BMRS only (`WINDFOR` forecasts, `FUELHH` wind actuals) for January 2026.

## Live app
Frontend url - https://wind-forecast-gridbricks.vercel.app/
Backend url - https://kjhwr-0x7m.onrender.com/

## AI tools
This project was built with AI assistance (Claude Code). 

## Files and directories

| Path | What it is |
| --- | --- |
| `backend/` | Python FastAPI service |
| `backend/app/main.py` | API routes: `/health`, `/api/forecast/{day}`, `/api/metrics`, `/api/buffer/{day}` |
| `backend/app/config.py`, `schemas.py` | Settings (env vars) and response models |
| `backend/app/ingest/` | `elexon.py` fetches from Elexon, `snapshot.py` writes a snapshot, `diff.py` compares two snapshots |
| `backend/app/analysis/` | `selection.py` (latest forecast at or before the cutoff) and `metrics.py` (error metrics and buffer) |
| `backend/scripts/bias_check.py` | Checks whether the forecast-vs-actual gap is a level offset or a timing/join problem |
| `backend/tests/` | Unit and API tests (pytest) |
| `backend/Dockerfile`, `requirements*.txt`, `pyproject.toml` | Backend image, dependencies, ruff and pytest settings |
| `frontend/` | React + Vite + TypeScript UI |
| `frontend/src/App.tsx`, `queries.ts`, `api.ts` | Page, data fetching and API client |
| `frontend/src/components/` | `ForecastChart.tsx`, `MetricsPanel.tsx` and small UI parts in `ui/` |
| `frontend/Dockerfile`, `vercel.json` | Front-end image and Vercel build settings |
| `backend/data/snapshots/` | Immutable data snapshots (parquet + `manifest.json`). One is committed and served by the deployed API |
| `docker-compose.yml` | Runs API (`:8000`) and UI (`:3000`) together |
| `render.yaml` | Render blueprint for the API |
| `.env.example` | Environment variables (copy to `.env`) |
| `Makefile` | Shortcuts: `up`, `api`, `web`, `test`, `lint`, `format`, `ingest`, `demo-video` |
| `.github/workflows/ci.yml` | Lint, backend tests and front-end build on every push and pull request |
| `slides.html`, `video-script.md`, `demo/` | Pitch slides, voiceover script, and scripts that record and merge the demo video |

## How to start

**With Docker (needs Docker with Compose):**

    cp .env.example .env
    make up        # same as: docker compose up --build

Then open the UI at <http://localhost:3000>. The API is at <http://localhost:8000> (interactive docs at `/docs`, health at `/health`).

**Without Docker (needs Python 3.12 and Node 20+):**

    python3 -m venv backend/.venv && . backend/.venv/bin/activate
    pip install -r backend/requirements-dev.txt
    (cd frontend && npm ci)
    make api       # API on :8000 (run in one terminal)
    make web       # UI on :5173 (run in another)

**Other commands:**

    make test      # backend tests
    make ingest    # fetch January 2026 from Elexon into a new snapshot (needs network; the committed snapshot is enough to run the app)

## Configuration

Copy `.env.example` to `.env`. `docker compose` reads it automatically. Backend variables are `CORS_ORIGINS` (comma-separated, whitespace trimmed), `DEFAULT_CUTOFF`, `SNAPSHOT_DIR` and `SNAPSHOT_ID` (optional pin; empty serves the newest snapshot). `VITE_API_URL` is a build-time front-end variable.

## Lint, format, CI

    pip install -r backend/requirements-dev.txt && (cd frontend && npm ci)
    make lint     # ruff (backend), eslint + prettier (frontend)
    make format

`.github/workflows/ci.yml` runs lint and the backend tests, then lint and the front-end build, on every push and pull request.

## Deploy

The API never calls Elexon at runtime. One snapshot (`backend/data/snapshots/20261102T080553Z`) is committed and baked into the API image.

**API on Render.** Create a Blueprint from this repo. `render.yaml` defines a Docker web service with the repository root as the build context (so `data/` is reachable), health check `/health`, and the env vars above. The container listens on `$PORT`. After the first deploy, set `CORS_ORIGINS` in the Render dashboard to the Vercel URL.

**Front end on Vercel.** Import the repo and set the project **Root Directory** to `frontend`. `frontend/vercel.json` sets install `npm ci`, build `npm run build` and output `dist`. Add the environment variable `VITE_API_URL` set to the Render service URL  for the Production environment, then redeploy so the build picks it up.

To serve new data: run `make ingest`, commit the new snapshot directory (add an un-ignore line to `.gitignore`), and update `SNAPSHOT_ID` in `render.yaml`.

## Data revisions check

Open question: are `FUELHH` or `WINDFOR` values revised after first publication?

Snapshots are immutable and carry a `fetched_at`, so two pulls of the same window can be diffed:

    python -m app.ingest.diff <snapshot_a> <snapshot_b>

Result (2026-11-02): two full pulls of the January 2026 window, 98 seconds apart (`20261102T080415Z` and `20261102T080553Z`), were **identical**: 18,688 `WINDFOR` rows (keyed on target time and publish time) and 1,488 `FUELHH` wind rows, with zero changed, added or removed. Treated as a non-issue for v1. Only the second snapshot is kept (it is the blessed one); the first was deleted as a byte-for-byte duplicate.

Limits of this check: the window is ten months old, so it shows the data is stable now. It cannot show whether values changed between first publication and today. `WINDFOR` also keeps every publish as its own row, so a new forecast is a new row, not a revision. If a pull of the same window ever differs, the diff prints both versions and the absolute MW differences. Re-run it against a later snapshot before relying on this.

## How the numbers are defined

- **Error** is `forecast - actual`. Positive bias means the forecast ran high.
- **Scored** half-hours are those with both a forecast available at the cutoff and an actual. Every response includes `coverage` so a buyer can see how many half-hours the figures rest on: `targets`, `scored`, `off_forecast_grid` (half-hours the forecast dataset never covers: `WINDFOR` is published hourly, so all the :30s), `no_forecast` (on-the-hour targets with nothing published by the cutoff) and `no_actual`. Missing values are never filled.
- **Procurement buffer** is an *unconditional* quantile of shortfall over all scored half-hours, where shortfall is `max(forecast - actual, 0)`. Half-hours in which wind met or beat the forecast count as zero. It is therefore **not** "the P90 of the shortfalls that occurred": if wind under-delivers in only 30% of half-hours, the unconditional P90 is much smaller than the P90 among those 30%. The unconditional form answers "how much extra would have covered the shortfall in 90% of half-hours", which is the sentence shown in the UI. `buffer.n_shortfall` reports how many half-hours had a shortfall.

- **Two buffer bases.** `/api/buffer/{day}` is the decision aid: it uses only errors a buyer could already see at the cutoff, meaning targets from 2026-01-01 whose actual had been published by then (a half-hour's actual is published when it ends), each scored against the forecast available at its own cutoff. The first day has no history. `/api/metrics` is the retrospective evaluation over a chosen range and includes days after any delivery day in it, so it is not a figure a buyer could have had.

## Is the bias a join bug?

Run `python -m scripts.bias_check` (from `backend/`). On snapshot `20261102T080553Z`: forecast targets fall only on the hour. The forecast averages 13,433 MW against 11,581 MW actual (ratio 1.16, correlation 0.93), and 85% of scored half-hours are over-forecast. Scaling the forecast by 0.855 cuts MAE from 2,127 to 1,227 MW. Shifting it by up to four hours either way changes MAE by at most 2% and leaves bias near 1,800 MW. Bias is positive in every hour of the day and every week and grows with wind level, and even the latest forecast ever published for each target is biased by +1,596 MW. That points to a systematic level or population difference between `WINDFOR` and `FUELHH`, not timing or a join error. It is one month of data, so the cause is not established.

Because the largest errors are all over-forecasts, the P90 absolute error and the P90 buffer coincide in the retrospective figures (4,306 MW): the buffer is mostly a bias story.

## Bias-adjusted view

The raw forecast stays the default. Choosing **Forecast view: Bias-adjusted** in the UI adds a green forecast line to the chart and recomputes the day statistics and the cutoff-based buffer on it.

- The adjustment is the mean error (forecast - actual) over the same history the cutoff-based buffer uses: scored targets from 2026-01-01 whose actuals had been published by the cutoff. It is subtracted from every forecast of the delivery day and floored at 0 MW, so it uses no information from after the decision. The first day has no history and is not adjusted.
- API: `/api/forecast/{day}` returns `adjustment_mw`, `adjusted_metrics` and `adjusted_mw` on each row. `/api/buffer/{day}?adjust=true` computes the buffer after removing the same bias from the history's forecasts (`adjusted` and `adjustment_mw` are in the response). `/api/metrics` is unchanged and still raw.
- Limits: this removes a constant level only. The bias grows with wind level and is not constant, so on a low-wind day the correction can overshoot. On 2026-01-15 at the 09:00 cutoff the learned adjustment is 1,911 MW against a day bias of +1,025 MW, which leaves the adjusted forecast 886 MW low for that day (MAE 1,025 to 916 MW) and cuts the P90 buffer from 4,788 to 2,877 MW. The cause of the bias is still not established, so treat the adjusted view as a sensitivity check, not a corrected forecast.

## API input rules

Dates are validated as dates and must fall within January 2026, `start` must not be after `end`, `quantile` must be between 0 and 1, and `cutoff` must be `HH:MM`. Anything else returns 422. `snapshot` must be the id of an existing snapshot, otherwise 404. `adjust` on `/api/buffer/{day}` is a boolean (default false). Parsed snapshots are cached in memory by id, which is safe because snapshots are immutable.
