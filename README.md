# Divvy Backend

REST API for Divvy: an AI-assisted finance tracker for personal and group expenses, with receipt upload and structured extraction.

This repository contains the **backend only** (FastAPI). A separate client (for example a React app) is not part of this repo.

## Problem statement

Tracking shared expenses is often slow and error-prone. Manual receipt entry makes it unclear who paid, who owes what, and how to split costs fairly.

## Features

- User registration, JWT access/refresh tokens, optional Google OAuth, and email verification
- Groups, memberships, group expenses, and flexible splits (including itemized splits)
- Receipt pipeline: optional local YOLO-based crop (`detector.pt`), then **Anthropic Claude** for structured line items (items, prices, quantities); uploads via MinIO
- Virtual cards and **Stripe** integration; currency rates updated on a daily schedule (APScheduler)
- Audit logging for sensitive actions; group media stored in object storage

## Technology stack (this repo)


| Area           | Choice                                                        |
| -------------- | ------------------------------------------------------------- |
| Runtime        | Python 3.13 (see `Dockerfile`)                                |
| API            | FastAPI, Uvicorn                                              |
| Database       | PostgreSQL (async SQLAlchemy + Alembic migrations)            |
| Object storage | MinIO (S3-compatible)                                         |
| OCR / AI       | Ultralytics YOLO (optional), Anthropic API (`CLAUDE_API_KEY`) |
| Payments       | Stripe                                                        |
| Jobs           | APScheduler (e.g. currency rate refresh at 00:30 UTC)         |


Redis is **not** used in this codebase. Hosting (for example AWS EC2) is deployment-specific and not prescribed here.

## Configuration

Create a `.env` file in the project root (see `app/core/config.py` for the full list). The application loads it automatically.

**Required for a minimal boot:**


| Variable       | Purpose                                                                          |
| -------------- | -------------------------------------------------------------------------------- |
| `DATABASE_URL` | Async SQLAlchemy URL, e.g. `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME` |
| `SECRET_KEY`   | Signing key for JWTs                                                             |


**Common optional / feature-specific variables:**


| Variable                                                          | Purpose                                                                                             |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `CLAUDE_API_KEY`, `CLAUDE_MODEL_ID`, `CLAUDE_MAX_TOKENS`          | Receipt extraction via Anthropic                                                                    |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`          | File storage                                                                                        |
| `STRIPE_SECRET_KEY`                                               | Stripe                                                                                              |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Google login                                                                                        |
| `GOOGLE_EMAIL_FROM`, `GOOGLE_EMAIL_PASSWORD`                      | Outbound email (e.g. verification)                                                                  |
| `BACKEND_DOMAIN`, `FRONTEND_DOMAIN`                               | URLs for redirects and links (defaults include `http://localhost:8001` and `http://localhost:3000`) |


When using Docker Compose, point `DATABASE_URL` at the DB service (inside the compose network), for example:

`postgresql+asyncpg://divvy:divvy@divvy-db:5432/divvy-db`

When running the API on the host against Compose’s PostgreSQL, use the published port `**5601`** (mapped from container `5432`), for example:

`postgresql+asyncpg://divvy:divvy@localhost:5601/divvy-db`

MinIO in Compose is exposed on `**9000**` (API) and `**9001**` (console); defaults in `compose.yaml` use user/password `divvyminio`.

## Installation

### Option 1: Docker Compose (recommended)

```bash
git clone https://github.com/fredr1x/divvy-backend.git
cd divvy-backend
# Create .env with at least DATABASE_URL, SECRET_KEY, and MinIO/Claude keys as needed.
docker compose up --build -d
```

The API listens on `**http://localhost:8001**`. Migrations run automatically via `entrypoint.sh` before Uvicorn starts.

### Option 2: Local Python

```bash
git clone https://github.com/fredr1x/divvy-backend.git
cd divvy-backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

You still need PostgreSQL (and optionally MinIO) reachable per your `.env`.

## Usage

1. Start the stack (Compose or local Uvicorn + dependencies).
2. `**GET /**` — health payload `{"status":"ok"}`.
3. `**http://localhost:8001/docs**` — Swagger UI; `**/redoc**` — ReDoc.

Notable route prefixes include `/auth`, `/users`, `/groups`, `/user-groups`, `/group-expenses`, `/expense-split`, `/group-media`, `/minio`, `/virtual-card`, and `**POST /scan-receipt**` (OCR; requires an authenticated, verified user).

## Further reading

- `AUDIT.md` — internal audit notes on structure and git history.

