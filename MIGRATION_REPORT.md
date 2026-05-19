# Migration Report

## Summary

The standalone `PROTAC_BUILDER/` app remains isolated from the parent VLISEMOD codebase. Phase 2 completed the first major cleanup pass after the initial extraction, and Phase 2.2 restored the original API Builder and DeepPK reporting flow:

- canonical routes now use `/builder`, `/api-builder`, `/api-docs`, `/about`, and `/api/...`
- `/copy/...` remains only as a compatibility layer
- a shared `base.html` now provides the common shell
- nav, footer, popup, and global loader are centralized
- the usage counter now reads `/api/protac/builder/usage`
- historical usage was migrated into a verified seed JSON
- the old VLISEMOD login-dependent Get Parameters flow was restored as a standalone DeepPK pipeline behind `/api/deeppk/run`

## Phase 2.1 Regression Fixes

- removed global ChemDoodle/COPYstyles leakage from `base.html`
- restored the About page content and styling without ChemDoodle assets
- restored API Builder page asset scoping so ChemDoodle only loads where intended
- replaced the skeletal API docs page with a styled standalone reference page
- corrected the popup counter to use the verified parent `static/data/PROTAC_log.csv` row count only
- removed the fabricated combined seed logic that produced the incorrect 47k counter

## Phase 2.2 API Builder + DeepPK Restoration

- restored [templates/api_builder.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/api_builder.html) from the original parent `templates/COPYbuilder.html`
- restored the API welcome modal, usage counter, original loading overlay, and batch workflow
- moved API Builder page logic into [static/js/api-builder.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/api-builder.js)
- removed `/api-builder` dependence on main builder `COPYscripts.js`, which eliminated the page-specific console spam
- copied and wired the original DeepPK pipeline scripts into [tools/deeppk/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk)
- added per-request job folders under [outputs/deeppk_reports/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/outputs/deeppk_reports)
- restored downloadable PDF output and preserved supplemental RDKit descriptors in the UI response

## Files Created In Phase 2

- [protac_builder/api_routes.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/api_routes.py)
- [protac_builder/legacy_routes.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/legacy_routes.py)
- [protac_builder/route_impl.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/route_impl.py)
- [protac_builder/admet.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/admet.py)
- [protac_builder/usage.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/usage.py)
- [templates/base.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/base.html)
- [templates/partials/_nav.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_nav.html)
- [templates/partials/_footer.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_footer.html)
- [templates/partials/_global_loader.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_global_loader.html)
- [templates/partials/_builder_popup.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_builder_popup.html)
- [templates/builder.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/builder.html)
- [templates/api_builder.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/api_builder.html)
- [templates/api_docs.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/api_docs.html)
- [templates/about.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/about.html)
- [static/css/protac-theme.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-theme.css)
- [static/css/protac-nav-footer.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-nav-footer.css)
- [static/css/protac-modal.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-modal.css)
- [static/css/protac-loader.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-loader.css)
- [static/js/protac-nav.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-nav.js)
- [static/js/protac-counter.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-counter.js)
- [static/js/protac-loader.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-loader.js)
- [static/js/protac-admet.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-admet.js)
- [ROUTE_MIGRATION.md](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/ROUTE_MIGRATION.md)
- [protac_builder/deeppk.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/deeppk.py)
- [static/js/api-builder.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/api-builder.js)
- [DEEPPK_RESTORE_AUDIT.md](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/DEEPPK_RESTORE_AUDIT.md)

## Files Updated In Phase 2

- [app.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/app.py)
- [protac_builder/routes.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/routes.py)
- [protac_builder/io_utils.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/io_utils.py)
- [protac_builder/paths.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/paths.py)
- [static/js/COPYscripts.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/COPYscripts.js)
- [templates/ligand_editor.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/ligand_editor.html)
- [templates/ligase_ligandalyzer.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/ligase_ligandalyzer.html)
- [templates/view_ligase.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/view_ligase.html)
- [templates/api_builder.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/api_builder.html)
- [README.md](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/README.md)
- [ROUTE_INVENTORY.md](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/ROUTE_INVENTORY.md)
- [DEPENDENCY_AUDIT.md](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/DEPENDENCY_AUDIT.md)
- [.gitignore](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/.gitignore)

## Files Copied From Original VLISEMOD In Phase 2

No large new dataset copy was needed in Phase 2.

The main reuse path was internal reuse of already-copied standalone assets plus sanitized migration of the verified historical build count from the parent VLISEMOD `static/data` folder into:

- [static/data/protac_builder_usage_seed.json](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/protac_builder_usage_seed.json)

That seed stores the verified historical build row count only, not raw user/session/IP history.

Additional files copied in Phase 2.2:

- parent `templates/COPYbuilder.html` -> [templates/api_builder.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/api_builder.html) as the restoration source
- parent `SmilesDrugProps.py` -> [tools/deeppk/SmilesDrugProps.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/SmilesDrugProps.py)
- parent `JSONANALYZER.py` -> [tools/deeppk/JSONANALYZER.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/JSONANALYZER.py)
- parent `DeepPKDisplay.py` -> [tools/deeppk/DeepPKDisplay.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/DeepPKDisplay.py)

Intentionally not copied for the DeepPK restore:

- `LigandSmiles.py` was audited but not required for Get Parameters because the restored workflow operates directly on the generated PROTAC SMILES

## Intentional Exclusions

Still excluded:

- `users.db`
- `users_info/`
- `viral_data.db`
- Flask-Login auth/session state
- `torch`
- `transformers`
- Llama model loading
- `DRUGapp.py`
- parent VLISEMOD route files
- historical raw user/session databases

## Usage Counter Migration

The builder popup no longer depends on directly reading a local public CSV file.

New behavior:

- frontend uses `/api/protac/builder/usage`
- backend reads a verified seed written into [static/data/protac_builder_usage_seed.json](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/data/protac_builder_usage_seed.json)
- verified historical source file: parent VLISEMOD `static/data/PROTAC_log.csv`
- counting rule: non-header CSV rows
- verified historical build count: `127`
- current total is `seed_total + successful local standalone build actions`
- template download counts remain separate and do not affect the popup build counter

## DeepPK / Get Parameters

The standalone Get Parameters flow now uses the restored DeepPK pipeline:

- canonical endpoint: `POST /api/deeppk/run`
- legacy alias: `POST /run-drug-analysis`
- supplemental local descriptor endpoint retained: `POST /api/admet/run`
- input: SMILES or MOL block
- output: JSON with:
  - `pdf_url`
  - `deeppk.pdf_url`
  - `deeppk.csv_url`
  - `deeppk.clean_csv_url`
  - `deeppk.json_url`
  - `deeppk.svg_url`
  - `rdkit_descriptors`
  - `warnings`

Phase 2.2 validation confirmed:

- `POST /api/deeppk/run` returned `200` for `{"smiles":"CCO"}`
- a PDF report was written and downloaded successfully
- the PDF response size was non-zero at `2,088,952` bytes for the validation job

## UI Refactor

Shared layout now comes from:

- [templates/base.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/base.html)
- [templates/partials/_nav.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_nav.html)
- [templates/partials/_footer.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_footer.html)
- [templates/partials/_global_loader.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_global_loader.html)
- [templates/partials/_builder_popup.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_builder_popup.html)

The linker modal was widened and restyled via [static/css/protac-modal.css](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/css/protac-modal.css).

## Tests Run

- `python -m compileall .`
- `python app.py`
- direct Python DeepPK wrapper validation via `protac_builder.deeppk.run_deeppk_pipeline("CCO")`
- canonical route checks for `/`, `/builder`, `/api-builder`, `/api-docs`, `/about`, `/ligase-ligandalyzer`, `/healthz`
- clean API checks for `/api/linkers/curated`, `/api/ligases`, `/api/protac/builder/usage`, `/api/protac/builder/template/download-count`
- POST checks for `/api/molecule/smiles-to-mol`, `/api/molecule/mol-to-smiles`, `/api/deeppk/run`
- DeepPK artifact download checks for `/api/deeppk/download/<job_id>/JARI_PROTAC_Report.pdf` and `/api/deeppk/download/<job_id>/DeepPK_Cleaned_Output.csv`
- legacy checks for `/copy/COPYindex`, `/copy/COPYbuilder`, `/copy/api`, `/copy/about`, and `/copy/convert_smiles_to_mol`
- legacy DeepPK alias check for `POST /run-drug-analysis`

## Known Limitations

- the active templates still carry a fair amount of legacy inline CSS/JS even after the shared-shell refactor
- `/api-builder` is restored and quiet, but it still carries a large amount of original inline CSS that could be modularized later
- recruiter converted-session loading still depends on an external session source unless configured locally
- hunter-job bridge positive-path testing still needs a real job directory
- DeepPK still depends on the external University of Queensland service, so slow upstream API responses can make a request take up to the configured wait limit

## Phase 2.3 Popup + DeepPK UX Polish

- restored the original builder popup appearance and copy while keeping the count backend-driven via `GET /api/protac/builder/usage`
- changed the builder Get Parameters workflow from blocking DeepPK-first to RDKit-first:
  - local RDKit descriptors render immediately from `POST /api/admet/run`
  - DeepPK report generation follows through `POST /api/deeppk/run`
- added a PoseView-style inline loader with rotating related-tool and paper links
- replaced browser alerts with inline DeepPK failure cards and preserved the RDKit table on retryable failures
- added structured DeepPK JSON failures with stage tracking and traceback logging
- stopped `/api/recruiter/converted/None` by normalizing empty session values in the builder template and frontend loader
- validation on May 19, 2026:
  - `python -m compileall .` passed
  - `python app.py` hit `Operation not permitted` in this sandbox after startup, so Flask `test_client()` was used for route validation
  - `/builder`, `/api-builder`, `/api-docs`, `/about`, `/healthz` returned `200`
  - `POST /api/admet/run` with `CCO` returned `200`
  - `POST /api/deeppk/run` with `CCO` returned `200`
  - current usage response in this checkout is `seed_total=127`, `local_actions=5`, `total=132`

## Recommended Next Cleanup

- continue moving page-specific inline CSS/JS into dedicated static files
- split `route_impl.py` further so fewer legacy handlers are reused internally
- add automated Flask tests for canonical and legacy route parity
- add optional PDF report generation for ADMET output
- consider replacing the remaining legacy ChemDoodle page script patterns with smaller page-specific modules

## Phase 2.4 API Docs + Reference Finalization

- updated `/api-docs` to reflect the live standalone route surface and user-facing behavior
- separated RDKit and DeepPK responsibilities in the docs:
  - `POST /api/admet/run` for immediate local descriptors
  - `POST /api/deeppk/run` for DeepPK report generation
- documented DeepPK success outputs as PDF, CSV, cleaned CSV, JSON, and SVG links
- documented DeepPK failures as structured JSON responses
- documented `GET /api/protac/builder/usage` as the counter source
- clarified that only successful PROTAC generation increments usage
- clarified that `/copy/...` remains compatibility-only
- re-verified the frontend Get Parameters hook sequence against the live builder implementation

## Phase 2.5 Client-Facing API Docs

- rewrote `/api-docs` as an external integration page aimed at users calling the API from local scripts, notebooks, services, and apps
- removed visible compatibility-route and migration-focused language from the browser-facing docs page
- added Python-first quick-start examples, end-to-end RDKit then DeepPK examples, and clearer base URL guidance
- improved docs-page readability without changing the underlying Get Parameters execution order
