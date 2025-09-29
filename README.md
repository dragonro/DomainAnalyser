# Domain Analyzer

Domain Analyzer is a FastAPI service with a static web UI that inspects DNS records for a domain, highlights email/productivity providers, and stores previous lookups. It can optionally brute-force subdomains from a word list and visualize the results in the bundled HTML reports.

## Features
- Validate the existence of domains before running deeper analysis.
- Inspect apex DNS records (A, AAAA, MX, TXT, NS, CNAME) and classify the providers you rely on.
- Enumerate subdomains asynchronously using configurable word lists.
- Persist past lookups to SQLite so you can revisit or compare domains later.
- Serve a lightweight frontend (`index.html`, `insight.html`, `report.html`) directly from the same FastAPI app.

## Project Layout
```
.
├── backend/
│   ├── app/                 # FastAPI application, database helpers, domain services
│   ├── data/                # SQLite database lives here (persisted via volume mount)
│   ├── requirements.txt     # Python dependencies
│   └── wordlists/           # Default subdomain dictionaries
├── Dockerfile               # Container image definition
├── docker-compose.yml       # Runs the published image with persistent storage
├── run.sh                   # Helper to run the backend locally in a virtualenv
└── build_push_container.sh  # Script to build/tag/push the Docker image
```

## Getting Started

### Prerequisites
- Docker and Docker Compose (v2 syntax) installed locally.
- Alternatively, Python 3.11+ if you plan to run the API directly.

### Run with Docker Compose
```bash
docker compose up -d
```
This pulls `adrianbega/domana:0.4`, exposes the API at http://localhost:3000, and mounts `./backend/data` into the container to persist the SQLite database.

Visit http://localhost:3000 to load the UI, or call the API directly:
- `POST /api/lookup` — quick domain verification.
- `GET /api/domains/{domain}` — run a full analysis, optionally specifying `include_subdomains`, `wordlist`, and `max_concurrency` query parameters.
- `GET /api/reports` — list stored lookups.
- `GET /api/reports/{domain}` — fetch the latest cached report.

### Run Locally (no Docker)
```bash
./run.sh
```
The script creates a virtual environment in `backend/.venv`, installs dependencies from `backend/requirements.txt`, and starts Uvicorn on http://0.0.0.0:3000.

### Building & Publishing an Image
Use `build_push_container.sh` to rebuild the image from source and push to Docker Hub. Update the `TAG` value in the script as needed before running it:
```bash
./build_push_container.sh
```

## Development Notes
- DNS enumeration uses asyncio and respects the `max_concurrency` query parameter to avoid overloading resolvers.
- Known provider fingerprints live in `backend/app/services/providers/providers.json`; adjust patterns there to improve detection.
- Results are stored in SQLite at `backend/data/domain_analyser.db`. Mount or back up this directory if you need persistence.

## License
This project proprietary, and belongs to DualBytes.
Author: Adrian Bega.

