# Dependency Audit

## Phase 2.1 Regression Fixes

- `base.html` now loads only shared global assets
- ChemDoodle and `COPYstyles.css` are page-scoped to builder/editor pages
- `/about` and `/api-docs` no longer load ChemDoodle assets
- the usage counter now uses the verified legacy `static/data/PROTAC_log.csv` row count instead of combined aggregate logic

## Phase 2.2 API Builder + DeepPK Restoration

- `/api-builder` was restored from the original parent `COPYbuilder.html`
- API Builder page logic now lives in [static/js/api-builder.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/api-builder.js)
- the restored DeepPK pipeline now runs through:
  - [tools/deeppk/SmilesDrugProps.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/SmilesDrugProps.py)
  - [tools/deeppk/JSONANALYZER.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/JSONANALYZER.py)
  - [tools/deeppk/DeepPKDisplay.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/DeepPKDisplay.py)
- the standalone wrapper is [protac_builder/deeppk.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/deeppk.py)

## Python Imports Retained

Core framework and utility imports retained in the standalone app:

- `flask`
- `pandas`
- `numpy`
- `requests`
- `PIL`
- `rdkit`
- `pathlib`
- `functools`
- `datetime`
- `io`
- `zipfile`
- `traceback`
- `secrets`
- `base64`
- `re`
- `os`
- `shutil`
- `subprocess`

Phase 2-specific retained modules:

- `json`
- `csv`
- `secrets`
- `datetime`

New internal modules added in Phase 2:

- [protac_builder/api_routes.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/api_routes.py)
- [protac_builder/legacy_routes.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/legacy_routes.py)
- [protac_builder/route_impl.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/route_impl.py)
- [protac_builder/admet.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/admet.py)
- [protac_builder/usage.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/usage.py)
- [protac_builder/deeppk.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/deeppk.py)

## Python Imports Removed

The standalone app intentionally does not import:

- `torch`
- `transformers`
- `flask_login`
- VLISEMOD auth/session helpers
- `DRUGapp`
- VLISEMOD viral database helpers

Also not retained:

- `pubchempy`
- `seaborn`
- `LigandSmiles.py` runtime dependencies, because that script was audited but not needed for the restored Get Parameters flow

## CSV Dependencies

Required:

- [data/linkers.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/data/linkers.csv)
  Used for curated linker listing and builder templates.

- [data/output_csvs/Ligand_Atoms_Smiles_part1.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/data/output_csvs/Ligand_Atoms_Smiles_part1.csv)
  Used for ligand lookup and editor population.

Optional but copied:

- [static/data/API_Linkers.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/API_Linkers.csv)
  Used by template download endpoint.

Runtime-created:

- [static/data/Generated_PROTACs.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/Generated_PROTACs.csv)
- [static/data/PROTAC_log.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/PROTAC_log.csv)
- [static/data/protac_builder_usage.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/protac_builder_usage.csv)
- [static/data/protac_api_downloads.csv](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/protac_api_downloads.csv)
- [static/data/protac_builder_usage_seed.json](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/protac_builder_usage_seed.json)
  Stores the verified historical build seed from parent `static/data/PROTAC_log.csv` using the counting rule `seed_total from parent legacy PROTAC_log.csv non-header rows + local standalone successful generated PROTAC rows`.

## SDF And PDB Dependencies

Copied and used:

- root ligase `.sdf` files under [Ligases/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/Ligases)
- supporting PDB files under [Ligases/PDB_Structures/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/Ligases/PDB_Structures)

Optional:

- recruiter-module files under [Ligases/MODULE/e3-recruiter-mod/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/Ligases/MODULE/e3-recruiter-mod)
- warhead hunter job folders under [static/hunter_jobs/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/hunter_jobs)

Graceful fallback behavior:

- missing ligase folder returns clean JSON error
- missing recruiter SDF returns clean JSON error with path hint
- missing hunter job returns clean JSON error with setup guidance

## Static And Template Dependencies

Templates copied:

- `COPYindex.html`
- `COPYbuilder.html`
- `COPYapi.html`
- `copy_about.html`
- `ligand_editor.html`
- `ligase_ligandalyzer.html`
- `view_ligase.html`
- `PROTAC_Builder_popup.html`
- `_tutorial_flyover.html`

Key static dependencies copied:

- `static/js/COPYscripts.js`
- `static/js/ChemDoodleWeb.js`
- `static/js/ChemDoodleWeb-uis.js`
- `static/css/COPYstyles.css`
- `static/css/ChemDoodleWeb.css`
- `static/css/jquery-ui-1.11.4.css`
- `static/images/`
- `static/linker_images/`
- `static/Ligase_Images/`
- `static/python/PrepFiles.py`
- `static/data/ligases.json`
- `static/data/recruiter_pdb_map.json`

Template adjustments made:

- fixed stylesheet reference in copied `ligand_editor.html`
- updated active templates to extend a shared [base.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/base.html)
- moved shared shell concerns into:
  - [static/css/protac-theme.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-theme.css)
  - [static/css/protac-nav-footer.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-nav-footer.css)
  - [static/css/protac-modal.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-modal.css)
  - [static/css/protac-loader.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-loader.css)
  - [static/js/protac-nav.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-nav.js)
  - [static/js/protac-counter.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-counter.js)
  - [static/js/protac-loader.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-loader.js)
  - [static/js/protac-admet.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-admet.js)
- restored `/api-builder` as its own standalone page shell so it can load ChemDoodle without inheriting the shared base assets
- updated visible internal URLs to use canonical standalone routes instead of `/copy/...`

## Runtime-Created Folders

Created automatically if missing:

- [uploads/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/uploads)
- [uploads/admet_reports/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/uploads/admet_reports)
- [uploads/deeppk/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/uploads/deeppk)
- [outputs/deeppk_reports/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/outputs/deeppk_reports)
- [logs/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/logs)
- [static/data/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data)
- [static/linker_images/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/linker_images)
- [static/Ligase_Images/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/Ligase_Images)
- [static/hunter_jobs/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/hunter_jobs)

## External Runtime Couplings Still Present

- `/api/recruiter/converted/<session_id>` uses an external base URL unless overridden by `PROTAC_CONVERTED_SESSION_BASE`
- `/api/warheadhunter/job/<job_id>` can optionally mirror from external `TARGET_BUILDER_JOBS_DIR`
- verified historical usage migration reads the parent VLISEMOD `static/data/PROTAC_log.csv` row count when available, but does not copy raw IP/user/session records into the standalone app

## Minimal Runtime Package Set

The final [requirements.txt](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/requirements.txt) includes:

- `Flask`
- `pandas`
- `numpy`
- `rdkit`
- `Pillow`
- `requests`
- `Werkzeug`
- `rich`
- `reportlab`
- `matplotlib`

No model-serving or VLISEMOD-specific auth/database packages are required.

## Phase 2.3 Popup + DeepPK UX Polish

- popup restoration stayed within the existing standalone frontend assets:
  - [templates/partials/_builder_popup.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_builder_popup.html)
  - [static/css/protac-modal.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-modal.css)
  - [static/js/protac-counter.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-counter.js)
- the RDKit-first Get Parameters flow depends on:
  - [protac_builder/admet.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/admet.py)
  - [protac_builder/deeppk.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/deeppk.py)
  - [tools/deeppk/DeepPKDisplay.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/DeepPKDisplay.py)
- DeepPK jobs now set `MPLCONFIGDIR` to a writable per-job directory, and `DeepPKDisplay.py` now tolerates empty pie-chart datasets so small validation molecules can still complete
- no parent VLISEMOD auth, database, `torch`, or `transformers` dependencies were reintroduced
- validation summary:
  - `python -m compileall .` passed
  - `POST /api/admet/run` returned descriptor JSON for `CCO`
  - `POST /api/deeppk/run` returned a successful PDF/CSV/JSON/SVG payload for `CCO`

## Phase 2.4 API Docs + Reference Finalization

- no new framework or server dependency was added for the docs refresh
- `/api-docs` remains template-driven in [templates/api_docs.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/api_docs.html) with lightweight inline styling and clipboard helpers only
- [protac_builder/admet.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/admet.py) now exposes a `descriptors` alias alongside `properties` for clearer public examples
- [protac_builder/deeppk.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/deeppk.py) now exposes a `links` alias alongside the existing `deeppk` object for clearer public examples
- docs now explicitly describe the RDKit-first + DeepPK-second browser flow without adding any VLISEMOD auth coupling
