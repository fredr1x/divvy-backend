# Divvy Project

AI-powered finance tracker for managing personal and group expenses with automated receipt OCR.

## Team members
ID: 230103074 Yerdaulet Amanbay \
ID: 230103277 Dias Izdibayev \
ID: 230103107 Alikhan Bissenov \
ID: 230103059 Nursanat Mussa

## Problem Statement
Tracking shared expenses is often slow and error-prone, especially for couples, roommates, trips, and group activities. Manual receipt entry creates ambiguity about who paid, who owes, and how to split costs fairly.

## Features
- Flexible expense splitting (equal, percentage-based, custom amounts)
- Group expense management and balance tracking
- Automated receipt capture and OCR extraction (items, prices, totals, taxes)
- AI-assisted receipt text extraction using Claude Code API

## Installation
### Option 1: Docker (Recommended)
```bash
git clone https://github.com/fredr1x/divvy-backend.git
cd divvy-backend
docker compose up --build -d
```

### Option 2: Local Python Setup
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

## Usage
1. Start the backend using Docker Compose or local Python setup.
2. Open `http://localhost:8001` to verify API health.
3. Open `http://localhost:8001/docs` for interactive Swagger API docs.
4. Use OCR endpoints to upload receipt images and extract text/data.

## Technology Stack
- Frontend: HTML, CSS, JavaScript, React
- Backend: Python, FastAPI
- Database: PostgreSQL, Redis
- Storage: MinIO (S3-compatible)
- Cloud/Hosting: AWS EC2
- Integrations: Stripe, Claude Code API (OCR workflow)
