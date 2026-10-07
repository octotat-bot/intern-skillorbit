# Deployment

The API runs on **Render** (gunicorn) and the frontend on **Vercel**. Both have free tiers.

## 1. Backend on Render

1. Push the repository to GitHub.
2. In Render choose **New > Blueprint** and select the repository. `render.yaml` at the repo root
   creates the `resume-analyzer-api` web service:
   - root directory `backend`
   - build: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
   - start: `gunicorn -c gunicorn.conf.py "app:create_app()"` (2 workers x 4 threads, app preloaded
     so spaCy loads once)
   - health check: `/api/health`
3. Set the secret variables when prompted:
   - `CORS_ORIGINS`: your Vercel URL, e.g. `https://resume-analyzer.vercel.app`
   - `GEMINI_API_KEY`: optional; leave empty to run rules-only
4. Deploy, then check `https://<service>.onrender.com/api/health` returns `{"status": "ok"}`.

Without the Blueprint, create a Python web service manually with the same root directory, build and
start commands (a `Procfile` is also included).

**Storage note:** the free plan's disk is ephemeral, so uploaded resumes disappear on restart or
redeploy. That is acceptable for a demo because analyses are recomputed on demand. For persistence,
attach a Render disk and set `DATABASE_PATH` to a path on it (e.g. `/var/data/resumes.db`).

**Cold starts:** free services sleep after inactivity; the first request can take about a minute.

## 2. Frontend on Vercel

1. In Vercel choose **Add New > Project**, import the repository, and set **Root Directory** to
   `frontend`. The framework (Vite) is detected; `vercel.json` adds the SPA rewrite so
   `/analysis/...` deep links work.
2. Add the environment variable `VITE_API_BASE_URL` = `https://<service>.onrender.com` (no trailing
   slash, no `/api`).
3. Deploy. Then make sure the Vercel URL is in the backend's `CORS_ORIGINS`.

## Environment variables

### Backend (`backend/.env`, Render)

| Variable | Default | Purpose |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed frontend origins |
| `DATABASE_PATH` | `instance/resumes.db` | SQLite file (relative to `backend/` or absolute) |
| `MAX_FILE_SIZE_MB` | `5` | Upload limit |
| `PORT` | `5000` | Port for `run.py` and gunicorn (Render sets it) |
| `FLASK_DEBUG` | `0` | `1` enables the debugger in `run.py` (never in production) |
| `LLM_PROVIDER` | `gemini` | `gemini` or `none` (disables AI mode) |
| `GEMINI_API_KEY` | empty | Enables AI mode; keep it secret |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Generation model |
| `AI_TIMEOUT_SECONDS` | `25` | Upper bound on an AI request |
| `EMBEDDING_PROVIDER` | `tfidf` | `tfidf` (local, shipped index) or `gemini` (needs key) |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Used when `EMBEDDING_PROVIDER=gemini` |
| `WEB_CONCURRENCY` | `2` | gunicorn workers |

### Frontend (`frontend/.env`, Vercel)

| Variable | Example | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `https://resume-analyzer-api.onrender.com` | Backend base URL |

Secrets are never committed: `.env` files are git-ignored and `.env.example` files document every
variable.

## Production smoke test

```bash
API=https://<service>.onrender.com
curl $API/api/health
curl -F "file=@backend/evaluation/samples/E01_strong_data_analyst.pdf" $API/api/resumes
curl "$API/api/resumes/1/analysis?role=data_analyst"
```
