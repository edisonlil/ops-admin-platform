# Render deployment

This project deploys to Render as a FastAPI backend. The Vue admin app can stay on
Netlify and call this service through `/api/*` redirects.

## Render service

Create a new Render Blueprint from this repository. Render reads `render.yaml` and
creates the `fg-agent-api` web service.

Required environment variables:

- `FG_AGENT_DATABASE_URL`: Supabase/Postgres connection string.
- `FG_AGENT_CORS_ORIGINS`: comma-separated frontend origins, for example
  `https://your-site.netlify.app,http://localhost:8001`. Set to `*` to disable
  cross-origin restrictions entirely.

Render will run:

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

## Database migration

Before pointing Render at Supabase, run the schema and import the local SQLite data.

1. Run `docs/supabase-schema.sql` in the Supabase SQL editor.
2. Set `FG_AGENT_DATABASE_URL` locally.
3. Import data:

```bash
python scripts/migrate_sqlite_to_supabase.py --truncate
```

## Health check

After deploy, verify:

```text
https://your-render-service.onrender.com/api/health
```

The response should report `database_backend` as `postgres`.
