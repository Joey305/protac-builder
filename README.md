# 🧬 PROTAC Builder

<p align="center">
  <strong>PROTAC Builder: A Flask-Based Web and API Platform for PROTAC-Like Molecule Construction, Recruiter/Linker Exploration, RDKit Descriptors, and DeepPK Report Generation</strong>
</p>

<p align="center">
  <em>A standalone molecular-design application for building PROTAC-like molecules, exploring curated E3 recruiter and linker data, and running client-facing API workflows for molecular descriptors and pharmacokinetic-style reports.</em>
</p>

<p align="center">
  <a href="https://protacbuilder.com">
    <img src="https://img.shields.io/badge/Launch-PROTACBuilder.com-06b6d4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Launch PROTAC Builder">
  </a>
  <a href="https://github.com/Joey305/protac-builder">
    <img src="https://img.shields.io/badge/GitHub-protac--builder-181717?style=for-the-badge&logo=github" alt="PROTAC Builder GitHub repository">
  </a>
  <a href="#quick-start">
    <img src="https://img.shields.io/badge/Get%20Started-Quick%20Start-orange?style=for-the-badge&logo=gnubash" alt="Quick start">
  </a>
  <a href="#api-overview">
    <img src="https://img.shields.io/badge/API-Client%20Ready-blueviolet?style=for-the-badge&logo=fastapi" alt="Client-ready API">
  </a>
</p>

<p align="center">
  <a href="https://warheadhunter.com">
    <img src="https://img.shields.io/badge/Companion%20Tool-Warhead%20Hunter-00e5ff?style=for-the-badge" alt="Warhead Hunter">
  </a>
  <a href="https://e3ligandalyzer.com">
    <img src="https://img.shields.io/badge/Companion%20Tool-E3%20Ligandalyzer-7c3aed?style=for-the-badge" alt="E3 Ligandalyzer">
  </a>
  <a href="https://vlisemod.com">
    <img src="https://img.shields.io/badge/Companion%20Tool-V--LiSEMOD-22c55e?style=for-the-badge" alt="V-LiSEMOD">
  </a>
</p>

<p align="center">
  <a href="mailto:jxs794@miami.edu?subject=PROTAC%20Builder%20Question%20%2F%20Collaboration">
    <img src="https://img.shields.io/badge/Contact-Joseph--Michael%20Schulz-blue?style=for-the-badge&logo=gmail" alt="Contact Joseph-Michael Schulz">
  </a>
</p>

---

<p align="center">
  <strong>Build degraders. Explore recruiters. Generate descriptors. Ship client-facing molecular APIs.</strong>
</p>

<p align="center">
  <em>From curated linker and E3 ligase data to RDKit-first molecular descriptors, DeepPK report generation, and PROTAC design workflows.</em>
</p>

---

<a id="overview"></a>

## 🚀 Overview

**PROTAC Builder** is a standalone Flask application for building **PROTAC-like molecules**, browsing curated **linker** and **E3 recruiter / ligase** data, and exposing client-facing molecular design APIs.

The application supports both interactive web workflows and programmatic REST-style workflows, including:

- web-based PROTAC construction,
- API-driven molecule generation,
- curated linker and recruiter lookup,
- RDKit molecular descriptor generation,
- DeepPK report generation,
- downloadable CSV / JSON / PDF / SVG artifacts,
- batch workflows, and
- deployable public API documentation.

The project is designed to separate the PROTAC Builder codebase from older VLISEMOD authentication, legacy app wiring, and unrelated model-training dependencies, keeping the repository focused, lighter, and easier to deploy.

---

<a id="why-protac-builder"></a>

## 🎯 Why PROTAC Builder?

PROTAC design sits at the intersection of target-ligand chemistry, E3 recruiter selection, linker geometry, physicochemical property balancing, and downstream ternary-complex modeling.

A practical degrader design tool needs to help answer questions such as:

> **Which recruiter should I use? Which linker is chemically plausible? What does the resulting molecule look like? Can I get fast descriptors and downstream reports from an API?**

PROTAC Builder was created to make that workflow more accessible by combining a web builder, curated molecular resources, and public-facing API endpoints in a single Flask application.

---

<a id="repository-navigation"></a>

## 🧭 Repository Navigation

<p align="center">
  <a href="#quick-start">
    <img src="https://img.shields.io/badge/Quick%20Start-Run%20Locally-orange?style=for-the-badge&logo=python" alt="Run locally">
  </a>
  <a href="#api-overview">
    <img src="https://img.shields.io/badge/API%20Overview-RDKit%20%2B%20DeepPK-06b6d4?style=for-the-badge" alt="API overview">
  </a>
  <a href="#deployment">
    <img src="https://img.shields.io/badge/Deployment-protacbuilder.com-22c55e?style=for-the-badge&logo=googlecloud" alt="Deployment">
  </a>
  <a href="#data-policy">
    <img src="https://img.shields.io/badge/Data%20Policy-Keep%20Repos%20Light-lightgrey?style=for-the-badge&logo=github" alt="Data policy">
  </a>
</p>

- [Overview](#overview)
- [Why PROTAC Builder?](#why-protac-builder)
- [Core capabilities](#core-capabilities)
- [Companion tool ecosystem](#companion-tool-ecosystem)
- [Conceptual workflow](#conceptual-workflow)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Environment configuration](#environment)
- [API overview](#api-overview)
- [API docs domain configuration](#api-docs-domain-configuration)
- [Data and output policy](#data-policy)
- [Deployment notes](#deployment)
- [Developer notes](#developer-notes)
- [Roadmap](#roadmap)
- [Citation](#citation)
- [Contact](#contact)

---

<a id="core-capabilities"></a>

## ✨ Core Capabilities

| Capability | Purpose |
|---|---|
| **Web PROTAC Builder** | Interactive browser-based construction of PROTAC-like molecules. |
| **API Builder** | Client-facing API workflow for submitting molecules and retrieving generated outputs. |
| **RDKit descriptors** | Fast molecular property and descriptor generation through `/api/admet/run`. |
| **DeepPK reports** | Downstream report generation with downloadable PDF, CSV, JSON, and SVG artifacts. |
| **Curated linker data** | Explore linker resources used for degrader construction and API workflows. |
| **E3 recruiter / ligase data** | Browse recruiter metadata and ligase-related assets for degrader design. |
| **Batch workflows** | Support larger-scale PROTAC generation and analysis workflows. |
| **Public API documentation** | `/api-docs` is designed as a cleaner public-facing integration page. |
| **Deployment-ready config** | Domain and CORS behavior can be adjusted through environment variables. |

---

<a id="companion-tool-ecosystem"></a>

## 🧬 Companion Tool Ecosystem

PROTAC Builder is part of a broader structure-guided molecular design ecosystem.

<p align="center">
  <a href="https://protacbuilder.com">
    <img src="https://img.shields.io/badge/PROTAC%20Builder-Degrader%20Construction%20%2B%20API-06b6d4?style=for-the-badge" alt="PROTAC Builder">
  </a>
</p>

<p align="center">
  <a href="https://warheadhunter.com">
    <img src="https://img.shields.io/badge/Warhead%20Hunter-Solvent%20Exposure%20%2B%20Exit%20Vectors-00e5ff?style=for-the-badge" alt="Warhead Hunter">
  </a>
  <a href="https://e3ligandalyzer.com">
    <img src="https://img.shields.io/badge/E3%20Ligandalyzer-E3%20Recruiter%20Ligand%20Analytics-7c3aed?style=for-the-badge" alt="E3 Ligandalyzer">
  </a>
  <a href="https://vlisemod.com">
    <img src="https://img.shields.io/badge/V--LiSEMOD-Viral%20Ligand%20Interaction%20Explorer-22c55e?style=for-the-badge" alt="V-LiSEMOD">
  </a>
</p>

Together, these tools support a connected induced-proximity design workflow:

```text
Protein-ligand structure
        ↓
Warhead / exit-vector analysis
        ↓
E3 recruiter and linker exploration
        ↓
PROTAC-like molecule generation
        ↓
RDKit descriptors and DeepPK-style reporting
        ↓
Ternary complex modeling and downstream evaluation
```

---

<a id="conceptual-workflow"></a>

## 🧩 Conceptual Workflow

PROTAC Builder is organized around a practical builder-to-API workflow:

```text
1. Select or provide molecular inputs
2. Explore curated linkers and E3 recruiter data
3. Generate PROTAC-like molecules
4. Run fast RDKit descriptor calculations
5. Optionally launch DeepPK report generation
6. Download generated CSV / JSON / PDF / SVG outputs
7. Use results for medicinal chemistry triage or downstream modeling
```

The browser **Get Parameters** flow is intentionally preserved as:

```text
POST /api/admet/run     → fast RDKit-first descriptor response
POST /api/deeppk/run    → slower DeepPK-style report generation
```

This keeps the user interface responsive while still allowing heavier reporting workflows to complete separately.

---

<a id="repository-layout"></a>

## 📦 Repository Layout

```text
protac-builder/
├── Ligases/                         # Curated ligase / recruiter-related assets
├── data/                            # Curated source data and molecule datasets
│   ├── linkers.csv
│   └── output_csvs/
├── logs/                            # Runtime logs; should remain git-ignored
├── outputs/
│   └── deeppk_reports/              # Generated DeepPK artifacts; git-ignored
├── protac_builder/                  # Application package / backend helpers
├── static/                          # CSS, JavaScript, images, downloadable assets
│   ├── data/
│   ├── images/
│   └── linker_images/
├── templates/                       # Flask HTML templates
├── tools/
│   └── deeppk/                      # DeepPK workflow helpers
├── uploads/                         # Runtime uploads; should remain git-ignored
├── .env.example                     # Example environment configuration
├── .gitignore                       # Ignore rules for generated/runtime files
├── DEEPPK_RESTORE_AUDIT.md          # DeepPK restoration notes
├── DEPENDENCY_AUDIT.md              # Dependency review notes
├── MIGRATION_REPORT.md              # Standalone migration summary
├── ROUTE_INVENTORY.md               # Route inventory
├── ROUTE_MIGRATION.md               # Route migration notes
├── app.py                           # Main Flask entry point
├── requirements.txt                 # Python dependencies
└── README.md                        # Project documentation
```

The application is organized as a deployable Flask project with separated templates, static assets, curated molecular data, runtime outputs, and DeepPK helper tooling.

---

<a id="quick-start"></a>

## ⚡ Quick Start

Clone the repository:

```bash
git clone https://github.com/Joey305/protac-builder.git
cd protac-builder
```

Create and activate a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Run the application:

```bash
python app.py
```

Open the local development URL:

```text
http://127.0.0.1:5069
```

Primary local routes:

| Route | Purpose |
|---|---|
| `/builder` | Main PROTAC Builder interface. |
| `/api-builder` | Browser-facing API Builder workflow. |
| `/api-docs` | Public API documentation and integration examples. |
| `/about` | Project information page. |
| `/healthz` | Lightweight deployment health check. |

---

<a id="environment"></a>

## 🔐 Environment Configuration

The application reads configuration from environment variables and can also load a local `.env` file when present.

Important variables:

| Variable | Purpose |
|---|---|
| `FLASK_SECRET_KEY` | Secret key for Flask sessions and production deployment. |
| `PORT` | Runtime port. Default local development uses `5069`. |
| `PROTAC_PUBLIC_BASE_URL` | Public URL shown in hosted API docs and examples. |
| `PROTAC_LOCAL_BASE_URL` | Local development URL shown in docs and examples. |
| `PROTAC_ALLOWED_ORIGINS` | CORS allowlist for deployed frontend origins. |
| `DEEPPK_MAX_WAIT_SECONDS` | Maximum wait time for DeepPK-style jobs. |
| `DEEPPK_CHECK_INTERVAL_SECONDS` | Polling interval for DeepPK job completion checks. |
| `TARGET_BUILDER_JOBS_DIR` | Runtime location for target-builder job outputs. |
| `PROTAC_CONVERTED_SESSION_BASE` | Runtime location for converted session assets. |

Recommended local `.env` starter:

```bash
FLASK_SECRET_KEY=replace-me-with-a-real-secret
PORT=5069
PROTAC_PUBLIC_BASE_URL=https://protacbuilder.com
PROTAC_LOCAL_BASE_URL=http://127.0.0.1:5069
PROTAC_ALLOWED_ORIGINS=http://127.0.0.1:5069,https://protacbuilder.com
DEEPPK_MAX_WAIT_SECONDS=120
DEEPPK_CHECK_INTERVAL_SECONDS=2
TARGET_BUILDER_JOBS_DIR=static/hunter_jobs
PROTAC_CONVERTED_SESSION_BASE=static/converted_sessions
```

---

<a id="api-overview"></a>

## 🔌 API Overview

PROTAC Builder includes client-facing API routes for descriptor calculation, DeepPK report generation, PROTAC generation, curated linker lookup, and ligase metadata access.

### Key Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/admet/run` | Run fast RDKit descriptor generation. |
| `POST` | `/api/deeppk/run` | Launch DeepPK-style report generation. |
| `GET` | `/api/deeppk/download/<job_id>/<filename>` | Download DeepPK artifacts. |
| `GET` | `/api/admet/download/<filename>` | Download RDKit CSV / JSON exports. |
| `POST` | `/api/protac/generate` | Generate a single PROTAC-like molecule. |
| `POST` | `/api/protac/builder/batch` | Run batch PROTAC builder workflows. |
| `GET` | `/api/linkers/curated` | Retrieve curated linker data. |
| `GET` | `/api/ligases` | Retrieve ligase / recruiter metadata. |

### Example: RDKit Descriptor Request

```bash
curl -X POST "${PROTAC_PUBLIC_BASE_URL:-https://protacbuilder.com}/api/admet/run" \
  -H "Content-Type: application/json" \
  -d '{
    "smiles": "CCOc1ccc2nc(S(N)(=O)=O)sc2c1",
    "name": "example_molecule"
  }'
```

### Example: DeepPK Report Request

```bash
curl -X POST "${PROTAC_PUBLIC_BASE_URL:-https://protacbuilder.com}/api/deeppk/run" \
  -H "Content-Type: application/json" \
  -d '{
    "smiles": "CCOc1ccc2nc(S(N)(=O)=O)sc2c1",
    "name": "example_molecule"
  }'
```

### Recommended Client Flow

For browser or client integrations, run:

```text
1. /api/admet/run
   └── returns fast RDKit-first molecular descriptors

2. /api/deeppk/run
   └── generates slower downloadable report artifacts
```

This preserves a fast initial user experience while still supporting deeper report generation.

---

<a id="api-docs-domain-configuration"></a>

## 🌐 API Docs Domain Configuration

The `/api-docs` page is designed to avoid hard-coded deployment text.

Use environment variables to control the rendered public and local base URLs:

```bash
PROTAC_PUBLIC_BASE_URL=https://protacbuilder.com
PROTAC_LOCAL_BASE_URL=http://127.0.0.1:5069
```

When the public domain changes, update the environment variable instead of editing the HTML template:

```bash
PROTAC_PUBLIC_BASE_URL=https://your-final-domain.com
```

This lets the same template support:

- local development,
- staging deployments,
- production deployment,
- future domain changes, and
- cleaner public API examples.

---

<a id="data-policy"></a>

## 🧹 Data and Output Policy

This repository should remain lightweight and source-code focused.

### Recommended to commit

- Flask application source code,
- API route logic,
- templates,
- frontend assets,
- lightweight curated linker / recruiter data,
- small static images required by the app,
- documentation,
- route inventory / migration notes,
- `.env.example`, and
- reproducible configuration examples.

### Recommended to exclude

- runtime logs,
- uploaded user files,
- generated DeepPK reports,
- large batch outputs,
- generated CSV / JSON downloads,
- private datasets,
- local `.env` files,
- credentials, tokens, secrets,
- cache folders, and
- temporary molecular design artifacts.

### Useful checks before committing

Check repository size:

```bash
du -sh .
du -h --max-depth=1 . | sort -hr
```

Find large files outside ignored folders:

```bash
find . -type f -size +50M \
  -not -path "./.git/*" \
  -not -path "./logs/*" \
  -not -path "./uploads/*" \
  -not -path "./outputs/*" \
  -exec ls -lh {} \;
```

Confirm runtime folders are ignored:

```bash
git check-ignore -v logs/example.log
git check-ignore -v uploads/example_file
git check-ignore -v outputs/deeppk_reports/example.pdf
```

---

<a id="deployment"></a>

## 🚀 Deployment Notes

Before production deployment:

1. Set a real Flask secret key.

```bash
FLASK_SECRET_KEY=use-a-real-random-secret
```

2. Set the public domain used in API documentation.

```bash
PROTAC_PUBLIC_BASE_URL=https://protacbuilder.com
```

3. Set allowed CORS origins.

```bash
PROTAC_ALLOWED_ORIGINS=https://protacbuilder.com
```

4. Ensure runtime folders are writable by the app process.

```text
logs/
uploads/
outputs/deeppk_reports/
static/hunter_jobs/
```

5. Keep generated outputs out of Git.

Runtime folders should exist on the server, but they should not be treated as source-code assets.

6. Use `/healthz` for deployment checks.

```bash
curl https://protacbuilder.com/healthz
```

---

<a id="developer-notes"></a>

## 🛠️ Developer Notes

This standalone app is intended to be independent of older VLISEMOD infrastructure.

It does **not** require:

- VLISEMOD auth,
- Flask-Login,
- `users.db`,
- `torch`,
- `transformers`, or
- `DRUGapp.py`.

Relevant internal documentation files:

| File | Purpose |
|---|---|
| `ROUTE_INVENTORY.md` | Current route inventory and endpoint tracking. |
| `ROUTE_MIGRATION.md` | Migration notes for route cleanup and standalone behavior. |
| `MIGRATION_REPORT.md` | Summary of the standalone migration. |
| `DEEPPK_RESTORE_AUDIT.md` | Notes related to DeepPK restoration and behavior. |
| `DEPENDENCY_AUDIT.md` | Dependency cleanup and package review notes. |

Recommended development loop:

```bash
source .venv/bin/activate
python app.py
```

Check Git status before committing:

```bash
git status --short
```

Commit changes:

```bash
git add .
git commit -m "Improve PROTAC Builder documentation"
git push
```

If the remote contains newer commits:

```bash
git pull --rebase origin main
git push
```

---

<a id="scientific-interpretation"></a>

## 🧠 Scientific Interpretation

PROTAC Builder provides computational design support, not automatic experimental validation.

Generated molecules, descriptor values, linker choices, and DeepPK-style reports should be interpreted alongside:

- target-ligand binding evidence,
- E3 recruiter suitability,
- linker attachment geometry,
- linker length and flexibility,
- physicochemical property balance,
- synthetic feasibility,
- ternary-complex formation hypotheses,
- cell permeability,
- degradation potency,
- selectivity, and
- experimental validation.

The platform is intended to support expert-guided degrader design and early triage, not replace medicinal chemistry judgment.

---

<a id="roadmap"></a>

## 🧭 Roadmap

Potential development directions:

- polished public examples in `/api-docs`,
- richer response schema documentation,
- hosted deployment on `protacbuilder.com`,
- Docker-based deployment,
- example client SDK snippets,
- expanded linker and recruiter metadata,
- additional batch workflow documentation,
- optional authentication for private deployments,
- improved frontend result visualizations,
- downloadable example reports,
- integration with Warhead Hunter exit-vector outputs,
- integration with E3 Ligandalyzer recruiter analytics, and
- manuscript-ready workflow documentation.

---

<a id="citation"></a>

## 🧬 Citation

A formal manuscript or software citation for PROTAC Builder can be added here when available.

For now, cite the GitHub repository and web platform:

```text
Schulz, J.-M. PROTAC Builder: A Flask-Based Web and API Platform for PROTAC-Like Molecule Construction, Recruiter/Linker Exploration, RDKit Descriptors, and DeepPK Report Generation. GitHub repository: https://github.com/Joey305/protac-builder. Web platform: https://protacbuilder.com.
```

<p align="center">
  <a href="https://protacbuilder.com">
    <img src="https://img.shields.io/badge/Web%20Platform-PROTACBuilder.com-06b6d4?style=for-the-badge&logo=googlechrome" alt="PROTAC Builder website">
  </a>
  <a href="https://github.com/Joey305/protac-builder">
    <img src="https://img.shields.io/badge/Source%20Code-GitHub-181717?style=for-the-badge&logo=github" alt="PROTAC Builder GitHub">
  </a>
</p>

---

<a id="contact"></a>

## 📬 Contact

For questions, bug reports, workflow support, or collaboration inquiries:

<p align="center">
  <a href="mailto:jxs794@miami.edu?subject=PROTAC%20Builder%20Question%20%2F%20Collaboration">
    <img src="https://img.shields.io/badge/Joseph--Michael%20Schulz-jxs794%40miami.edu-blue?style=for-the-badge&logo=gmail" alt="Email Joseph-Michael Schulz">
  </a>
  <a href="https://protacbuilder.com">
    <img src="https://img.shields.io/badge/Visit-PROTACBuilder.com-06b6d4?style=for-the-badge&logo=googlechrome" alt="Visit PROTAC Builder">
  </a>
</p>

---

<a id="repository-description"></a>

## 🧾 Repository Description

> PROTAC Builder is a standalone Flask web and API platform for PROTAC-like molecule construction, curated linker and E3 recruiter exploration, RDKit descriptor generation, and DeepPK-style molecular report workflows.

---

<a id="practical-takeaway"></a>

## 🙌 Practical Takeaway

Use PROTAC Builder when you need to move from:

```text
target ligand + E3 recruiter + linker idea
```

to:

```text
generated PROTAC-like molecule + descriptors + downloadable reports + client-facing API workflow
```

The platform helps connect interactive degrader design with deployable molecular APIs for real-world medicinal chemistry and induced-proximity research workflows.
