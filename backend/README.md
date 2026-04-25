# Backend (Flask + Postgres)

## Start Postgres with Docker (recommended)

From `nhatvibecoders/backend/`:

```bash
docker compose up -d
```

This runs Postgres on **127.0.0.1:5433** (container 5432) to avoid conflicts with any local Postgres you may already have on 5432.

To stop it:

```bash
docker compose down
```

To wipe the DB (deletes all data):

```bash
docker compose down -v
```

## Setup

Create a virtualenv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy env vars and edit as needed:

```bash
cp .env.example .env
```

## Run

This will auto-create tables on startup:

```bash
source .venv/bin/activate
python app.py
```

## Database spec

See `DATABASE_SPEC.md`.

## API

- `POST /users` body: `{ "username": "larry", "current_weight": 180.5 }`
- `GET /users/<username>`
- `PATCH /users/<username>` body: `{ "current_weight": 179.2 }`

Full API spec: `API_SPEC.md`.
