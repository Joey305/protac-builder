# PROTAC Builder

PROTAC Builder is a standalone Flask application for building PROTAC-like molecules, exploring curated recruiter and linker data, and running client-facing API workflows for RDKit descriptors and DeepPK report generation.

## Features

- Web PROTAC Builder
- API Builder
- client-facing REST API
- RDKit molecular descriptors
- DeepPK PDF/CSV/JSON/SVG reports
- curated linker/recruiter data
- batch workflows

## Quick Start

```bash
git clone <repo-url>
cd PROTAC_BUILDER
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Default local URL:

- [http://127.0.0.1:5069](http://127.0.0.1:5069)

Primary routes:

- `GET /builder`
- `GET /api-builder`
- `GET /api-docs`
- `GET /about`
- `GET /healthz`

## Environment

The app reads configuration from environment variables and also loads a local `.env` file when present.

Important variables:

- `FLASK_SECRET_KEY`
- `PORT`
- `PROTAC_PUBLIC_BASE_URL`
- `PROTAC_LOCAL_BASE_URL`
- `PROTAC_ALLOWED_ORIGINS`
- `DEEPPK_MAX_WAIT_SECONDS`
- `DEEPPK_CHECK_INTERVAL_SECONDS`
- `TARGET_BUILDER_JOBS_DIR`
- `PROTAC_CONVERTED_SESSION_BASE`

Default base URLs:

- Hosted docs/API examples: `https://protacbuilder.com`
- Local development examples: `http://127.0.0.1:5069`

`/api-docs` now reads those values from Flask config, so changing `PROTAC_PUBLIC_BASE_URL` or `PROTAC_LOCAL_BASE_URL` updates the rendered examples without editing the template.

## API Overview

Key endpoints:

- `POST /api/admet/run` for fast RDKit descriptors
- `POST /api/deeppk/run` for DeepPK report generation
- `GET /api/deeppk/download/<job_id>/<filename>` for DeepPK artifacts
- `GET /api/admet/download/<filename>` for RDKit CSV/JSON exports
- `POST /api/protac/generate` for single PROTAC generation
- `POST /api/protac/builder/batch` for batch workflows
- `GET /api/linkers/curated` for curated linker data
- `GET /api/ligases` for recruiter metadata

The browser Get Parameters flow is intentionally preserved as:

1. `POST /api/admet/run` first
2. `POST /api/deeppk/run` second

## Data And Runtime Files

Tracked source data includes:

- [data/linkers.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/data/linkers.csv)
- [data/output_csvs/Ligand_Atoms_Smiles_part1.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/data/output_csvs/Ligand_Atoms_Smiles_part1.csv)
- [static/data/API_Linkers.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/API_Linkers.csv)
- [static/data/protac_builder_usage_seed.json](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/protac_builder_usage_seed.json)
- [Ligases/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/Ligases)
- [static/images/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/images)
- [static/linker_images/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/linker_images)

Git-ignored runtime/generated outputs include:

- [logs/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/logs)
- [uploads/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/uploads)
- [outputs/deeppk_reports/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/outputs/deeppk_reports)
- [static/hunter_jobs/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/hunter_jobs)
- generated usage/download CSVs under [static/data/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data)

## Deployment Notes

- Set `FLASK_SECRET_KEY` to a real secret in production.
- Set `PROTAC_PUBLIC_BASE_URL` to the public site URL that should appear in `/api-docs`.
- Set `PROTAC_ALLOWED_ORIGINS` to the deployed frontend origins that should be allowed by CORS.
- Keep runtime directories writable for logs, uploads, and generated DeepPK outputs.
- DeepPK still depends on the external prediction workflow, so completion time can vary by job.

## Repo Notes

- This standalone app does not depend on VLISEMOD auth, Flask-Login, `users.db`, `torch`, `transformers`, or `DRUGapp.py`.
- Route inventory and migration notes are available in [ROUTE_INVENTORY.md](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/ROUTE_INVENTORY.md) and [ROUTE_MIGRATION.md](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/ROUTE_MIGRATION.md).
