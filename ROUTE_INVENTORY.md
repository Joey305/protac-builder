# Route Inventory

## Phase 2.1 Regression Fixes

- canonical pages remain `/builder`, `/api-builder`, `/api-docs`, and `/about`
- legacy `/copy/...` routes remain available
- `/api/protac/builder/usage` now reports the verified historical `PROTAC_log.csv` row count plus new standalone successful build actions only
- `/about` and `/api-docs` no longer load global ChemDoodle assets

## Phase 2.2 API Builder + DeepPK Restoration

- `/api-builder` is restored from the original parent `COPYbuilder.html`
- `/api-builder` no longer loads `COPYscripts.js`
- `POST /api/deeppk/run` now restores the original DeepPK/Get Parameters workflow
- `POST /run-drug-analysis` is a compatibility alias for the restored DeepPK route

## Canonical UI Routes

- `GET /`
- `GET /builder`
- `GET /api-builder`
- `GET /api-docs`
- `GET /about`
- `GET /ligand-editor`
- `GET /ligase-ligandalyzer`
- `GET /view-ligase`
- `GET /healthz`

## Canonical API Routes

- `GET /api/linkers/curated`
- `GET /api/ligases`
- `GET /api/ligase/render`
- `GET /api/ligase/raw/<name>`
- `GET /api/recruiter/<name>`
- `GET /api/recruiter/converted/<session_id>`
- `GET /api/ligand/smiles`
- `GET /api/ligand/data`
- `POST /api/ligand/modify`
- `POST /api/ligand/store`
- `POST /api/molecule/smiles-to-mol`
- `POST /api/molecule/mol-to-smiles`
- `POST /api/molecule/render-smiles`
- `POST /api/protac/generate`
- `POST /api/protac/download-smiles`
- `POST /api/protac/log`
- `POST /api/protac/batch-linkers`
- `POST /api/protac/structure/convert`
- `POST /api/protac/structure/mapped-smiles`
- `POST /api/protac/linkers/inspect`
- `POST /api/protac/builder/batch`
- `POST /api/protac/builder/cli`
- `GET /api/protac/builder/usage`
- `GET /api/protac/builder/template/linkers`
- `GET /api/protac/builder/template/download-count`
- `GET /api/warheadhunter/job/<job_id>`
- `POST /api/deeppk/run`
- `GET /api/deeppk/download/<job_id>/<filename>`
- `POST /api/admet/run`
- `GET /api/admet/download/<filename>`

## Legacy Compatibility Routes

- `GET /copy/COPYindex`
- `GET /copy/COPYindex/build`
- `GET /copy/COPYbuilder`
- `GET /copy/api`
- `GET /copy/about`
- `GET /copy/ligand_editor`
- `GET /copy/ligase_ligandalyzer`
- `GET /copy/view_ligase`
- `GET /copy/get_curated_linkers`
- `GET /copy/render_ligase`
- `GET /copy/get_ligand_smiles`
- `GET /copy/get_ligand_data`
- `GET /copy/load_recruiter/<name>`
- `GET /copy/load_converted/<session_id>`
- `GET /copy/list_ligases`
- `GET /copy/load_ligase_raw/<name>`
- `GET /copy/api/protac/builder/usage`
- `GET /copy/api/protac/builder/template/linkers`
- `GET /copy/api/protac/builder/template/download-count`
- `GET /copy/api/warheadhunter/job/<job_id>`
- `POST /copy/modify_ligand`
- `POST /copy/generate_protac`
- `POST /copy/download_smiles`
- `POST /copy/convert_smiles_to_mol`
- `POST /copy/convert_mol_to_smiles`
- `POST /copy/render_smiles`
- `POST /copy/store_ligand`
- `POST /copy/log_protac_frontend`
- `POST /copy/api/protac/batch_linkers`
- `POST /copy/api/protac/structure/convert`
- `POST /copy/api/protac/structure/mapped_smiles`
- `POST /copy/api/protac/linkers/inspect`
- `POST /copy/api/protac/builder/batch`
- `POST /copy/api/protac/builder/cli`
- `POST /run-drug-analysis`

## Legacy Routes Not Ported

- `POST /process`
- `GET /download/<filename>`
- `GET /ligase_details`
- `GET /protacability_page`

## Validation Status

Verified manually:

- `GET /`, `/builder`, `/api-builder`, `/api-docs`, `/about`, `/ligase-ligandalyzer`, `/healthz`
- `GET /api/linkers/curated`
- `GET /api/ligases`
- `GET /api/protac/builder/usage`
- `GET /api/protac/builder/template/download-count`
- `GET /api/protac/builder/template/linkers`
- `POST /api/molecule/smiles-to-mol`
- `POST /api/molecule/mol-to-smiles` bad-input path
- `POST /api/deeppk/run`
- `GET /api/deeppk/download/<job_id>/JARI_PROTAC_Report.pdf`
- `GET /api/recruiter/converted/None` invalid-session guard
- legacy redirects for `/copy/COPYindex`, `/copy/COPYbuilder`, `/copy/api`, `/copy/about`
- legacy POST compatibility for `/copy/convert_smiles_to_mol`
- legacy POST compatibility for `/run-drug-analysis`

Implemented but still needing richer end-to-end payloads or external data:

- `/api/protac/generate`
- `/api/protac/batch-linkers`
- `/api/protac/builder/batch`
- `/api/protac/builder/cli`
- `/api/warheadhunter/job/<job_id>` positive-path job loading

## Phase 2.3 Popup + DeepPK UX Polish

- `GET /api/protac/builder/usage` remains the sole popup count source
- the builder now uses `POST /api/admet/run` as the immediate RDKit step before `POST /api/deeppk/run`
- `POST /api/deeppk/run` now supports:
  - success payloads with PDF/CSV/cleaned CSV/JSON/SVG links
  - structured JSON failures with `error`, `details`, `stage`, `job_id`, `rdkit_descriptors`, and `retryable`
- `GET /api/recruiter/converted/<session_id>` now rejects blank and `None`-like IDs with a clean `400` JSON response

## Phase 2.4 API Docs + Reference Finalization

- `/api-docs` now documents the canonical front-facing routes as:
  - `/builder`
  - `/api-builder`
  - `/api-docs`
  - `/about`
  - `/healthz`
  - `/api/...`
- `/api/admet/run` is documented as the fast RDKit descriptor route
- `/api/deeppk/run` is documented as the DeepPK report route
- `/copy/...` and `/run-drug-analysis` remain documented as legacy compatibility only

## Phase 2.5 Client-Facing API Docs

- `/api-docs` now presents the public route surface as an external API guide organized by workflow instead of an internal route matrix
- the visible docs page now emphasizes Python and curl usage for:
  - `POST /api/protac/generate`
  - `POST /api/admet/run`
  - `POST /api/deeppk/run`
  - conversion endpoints
  - batch endpoints
  - operations endpoints
- browser-facing docs no longer mention `/copy/...` compatibility paths, while this inventory still retains the full route map for maintainers
