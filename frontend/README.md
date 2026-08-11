# Agricultural CV Research Dashboard

HTMX + Tailwind CSS dashboard visualizing the project's screening data, priority scores, batch status, and full-text extraction progress.

## Quick start

```powershell
cd frontend
uv run uvicorn backend.main:app --reload --port 8000
```

Or from project root:

```powershell
uv run uvicorn frontend.backend.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

## Structure

```
frontend/
├── backend/
│   ├── __init__.py
│   ├── main.py        # FastAPI app, static mount, CORS
│   ├── database.py    # Lazy CSV loader (pandas)
│   └── routes.py      # All API endpoints returning HTML fragments
├── public/
│   └── index.html     # Single-page app (HTMX + Tailwind CDN)
└── README.md
```

## Endpoints

| Route | Content |
|---|---|
| `GET /` | Redirects to dashboard |
| `GET /api/overview` | 6 stat cards + task/modality/domain tags |
| `GET /api/screening` | Full title/abstract decisions table |
| `GET /api/ranking` | Paper priority scores table |
| `GET /api/batches` | Screening batches table |
| `GET /api/extractions` | Full-text extraction status table |

## Data sources

All data is read live from `data/curated/` CSVs via `frontend/backend/database.py`. No preprocessing step needed — update the CSV and refresh the page.

## Dependencies

- fastapi, uvicorn, pandas (managed by `uv` from project root)
- HTMX 2.x, Tailwind CSS 3.x (loaded from CDN, no build step)
