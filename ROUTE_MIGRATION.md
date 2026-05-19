# Route Migration

## Phase 2.1 Regression Fixes

- canonical pages were visually restored after the Phase 2 route cleanup
- shared base assets are now scoped so ChemDoodle only loads on builder/editor pages
- usage metadata now reports the verified `static/data/PROTAC_log.csv` historical row count instead of a fabricated aggregate

## Phase 2.2 API Builder + DeepPK Restoration

- `/api-builder` was restored from the original parent `COPYbuilder.html`
- page-specific API Builder logic moved into `static/js/api-builder.js`
- `/run-drug-analysis` now maps to the restored DeepPK workflow instead of the temporary local-only descriptor route

| Old Route | New Route | Method | Status | Notes |
|---|---|---:|---|---|
| `/copy/COPYindex` | `/builder` | `GET` | Legacy redirect kept | Canonical main page is now `/builder` |
| `/copy/COPYindex/build` | `/builder?session=...` | `GET` | Legacy redirect kept | Converted-session query still supported |
| `/copy/COPYbuilder` | `/api-builder` | `GET` | Legacy redirect kept | Canonical interactive API builder page |
| `/copy/api` | `/api-docs` | `GET` | Legacy redirect kept | Canonical documentation page |
| `/copy/about` | `/about` | `GET` | Legacy redirect kept | Canonical about page |
| `/copy/ligand_editor` | `/ligand-editor` | `GET` | Legacy redirect kept | Query params preserved |
| `/copy/ligase_ligandalyzer` | `/ligase-ligandalyzer` | `GET` | Legacy redirect kept | Canonical recruiter browser |
| `/copy/view_ligase` | `/view-ligase` | `GET` | Legacy redirect kept | Canonical ligase detail page |
| `/copy/get_curated_linkers` | `/api/linkers/curated` | `GET` | Dual route kept | Old JSON path still works |
| `/copy/list_ligases` | `/api/ligases` | `GET` | Dual route kept | Old JSON path still works |
| `/copy/render_ligase` | `/api/ligase/render` | `GET` | Dual route kept | Old JSON path still works |
| `/copy/load_ligase_raw/<name>` | `/api/ligase/raw/<name>` | `GET` | Dual route kept | Old JSON path still works |
| `/copy/load_recruiter/<name>` | `/api/recruiter/<name>` | `GET` | Dual route kept | Old JSON path still works |
| `/copy/load_converted/<session_id>` | `/api/recruiter/converted/<session_id>` | `GET` | Dual route kept | External converted-session dependency remains |
| `/copy/get_ligand_smiles` | `/api/ligand/smiles` | `GET` | Dual route kept | Old JSON path still works |
| `/copy/get_ligand_data` | `/api/ligand/data` | `GET` | Dual route kept | Old JSON path still works |
| `/copy/modify_ligand` | `/api/ligand/modify` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/store_ligand` | `/api/ligand/store` | `POST` | Dual route kept | OPTIONS preserved |
| `/copy/convert_smiles_to_mol` | `/api/molecule/smiles-to-mol` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/convert_mol_to_smiles` | `/api/molecule/mol-to-smiles` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/render_smiles` | `/api/molecule/render-smiles` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/generate_protac` | `/api/protac/generate` | `POST` | Dual route kept | Counts toward usage summary on success |
| `/copy/download_smiles` | `/api/protac/download-smiles` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/log_protac_frontend` | `/api/protac/log` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/api/protac/batch_linkers` | `/api/protac/batch-linkers` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/api/protac/structure/convert` | `/api/protac/structure/convert` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/api/protac/structure/mapped_smiles` | `/api/protac/structure/mapped-smiles` | `POST` | Dual route kept | Counts toward usage summary on success |
| `/copy/api/protac/linkers/inspect` | `/api/protac/linkers/inspect` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/api/protac/builder/batch` | `/api/protac/builder/batch` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/api/protac/builder/cli` | `/api/protac/builder/cli` | `POST` | Dual route kept | No redirect for JSON clients |
| `/copy/api/protac/builder/usage` | `/api/protac/builder/usage` | `GET` | Dual route kept | Popup counter uses new canonical endpoint |
| `/copy/api/protac/builder/template/linkers` | `/api/protac/builder/template/linkers` | `GET` | Dual route kept | Download count is tracked separately from build activity |
| `/copy/api/protac/builder/template/download-count` | `/api/protac/builder/template/download-count` | `GET` | Dual route kept | Includes migrated seed count |
| `/copy/api/warheadhunter/job/<job_id>` | `/api/warheadhunter/job/<job_id>` | `GET` | Dual route kept | Graceful missing-job response preserved |
| `/run-drug-analysis` | `/api/deeppk/run` | `POST` | Legacy alias kept | Restored DeepPK PDF workflow, no VLISEMOD login required |

## Phase 2.3 Popup + DeepPK UX Polish

- builder popup restoration did not change the canonical route map
- builder Get Parameters now orchestrates:
  - `POST /api/admet/run` for immediate RDKit output
  - `POST /api/deeppk/run` for the slower DeepPK report workflow
- `/api/deeppk/run` now returns structured JSON failures instead of opaque HTML 500 pages
- `/api/recruiter/converted/<session_id>` now short-circuits invalid `None`-like session IDs
- validation on May 19, 2026 confirmed `200` responses for `/builder`, `/api-builder`, `/api-docs`, `/about`, `/healthz`, `POST /api/admet/run`, and `POST /api/deeppk/run` for `CCO`

## Phase 2.4 API Docs + Reference Finalization

- route documentation now positions:
  - `POST /api/admet/run` as the fast RDKit descriptor route
  - `POST /api/deeppk/run` as the DeepPK report route
  - `GET /api/protac/builder/usage` as the canonical usage counter route
- `/copy/...` and `/run-drug-analysis` remain mapped for compatibility, but `/api-docs` now treats them as non-canonical

## Phase 2.5 Client-Facing API Docs

- `/api-docs` was rewritten as a client-facing API guide for external callers rather than a visible compatibility reference
- public examples now focus on Python `requests`, curl, downloadable outputs, and realistic request or response payloads
- compatibility mapping remains tracked in this file, but that discussion no longer appears on the browser-facing docs page
