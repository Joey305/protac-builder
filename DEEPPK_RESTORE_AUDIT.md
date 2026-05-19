# DeepPK Restore Audit

## Summary

Phase 2.2 restores the original Get Parameters workflow as a standalone DeepPK pipeline inside [PROTAC_BUILDER](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER) without reintroducing VLISEMOD auth or `DRUGapp.py`.

Canonical route:

- `POST /api/deeppk/run`

Compatibility route:

- `POST /run-drug-analysis`

Download route:

- `GET /api/deeppk/download/<job_id>/<filename>`

## Original Parent Flow

Audited parent route:

- [../app.py](/Users/jxs794/Documents/VLISEMOD/app.py)

Original route behavior:

1. Read `smiles` from the request body.
2. Set `SMILES_INPUT` in the environment.
3. Run:
   - `python SmilesDrugProps.py`
   - `python JSONANALYZER.py`
   - `python DeepPKDisplay.py`
4. Wait for `JARI_PROTAC_Report.pdf`.
5. Return JSON containing `pdf_url`.

## Scripts Audited

Read from parent VLISEMOD:

- [../SmilesDrugProps.py](/Users/jxs794/Documents/VLISEMOD/SmilesDrugProps.py)
- [../JSONANALYZER.py](/Users/jxs794/Documents/VLISEMOD/JSONANALYZER.py)
- [../DeepPKDisplay.py](/Users/jxs794/Documents/VLISEMOD/DeepPKDisplay.py)
- [../LigandSmiles.py](/Users/jxs794/Documents/VLISEMOD/LigandSmiles.py)

Copied into standalone app:

- [tools/deeppk/SmilesDrugProps.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/SmilesDrugProps.py)
- [tools/deeppk/JSONANALYZER.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/JSONANALYZER.py)
- [tools/deeppk/DeepPKDisplay.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/DeepPKDisplay.py)

Not copied:

- [../LigandSmiles.py](/Users/jxs794/Documents/VLISEMOD/LigandSmiles.py)

Reason:

- `LigandSmiles.py` prepares upstream ligand/SMILES tables and is not part of the runtime Get Parameters flow, which operates directly on the generated PROTAC SMILES.

## Standalone Wrapper

Wrapper module:

- [protac_builder/deeppk.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/deeppk.py)

Responsibilities:

1. Accept SMILES or MOL block.
2. Convert MOL block to SMILES with RDKit if needed.
3. Create a per-request job directory:
   - [outputs/deeppk_reports/](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/outputs/deeppk_reports)
4. Generate `Protac.png` locally for the PDF report.
5. Copy `static/images/favicon.png` into the job-local `static/images/` folder expected by `DeepPKDisplay.py`.
6. Run the original scripts in sequence inside the job directory.
7. Return JSON with download URLs plus supplemental RDKit descriptors.

## Script Chain

### 1. SmilesDrugProps.py

Status:

- copied and retained
- patched to respect:
  - `DEEPPK_MAX_WAIT_SECONDS`
  - `DEEPPK_CHECK_INTERVAL_SECONDS`

Role:

- computes RDKit descriptors
- generates `Protac.svg`
- submits the molecule to the external DeepPK API
- polls for ADMET predictions
- writes:
  - `DeepPK_Predictions.csv`
  - `DeepPK_Predictions.json`

### 2. JSONANALYZER.py

Status:

- copied and retained
- patched to handle the current saved `DeepPK_Predictions.json` structure safely when `"Deep-PK Predictions"` is already a dictionary instead of a raw JSON string

Role:

- parses nested DeepPK prediction output
- groups results by category
- writes:
  - `DeepPK_Cleaned_Output.csv`

### 3. DeepPKDisplay.py

Status:

- copied and retained
- used directly for report generation

Role:

- reads `DeepPK_Cleaned_Output.csv`
- reads `Protac.png`
- reads `static/images/favicon.png`
- generates:
  - `JARI_PROTAC_Report.pdf`
  - `category_distribution.png`
  - `toxic_safe_distribution.png`
  - `metabolism_inhibitor_chart.png`
  - `metabolism_substrate_chart.png`

## Output Files

Each job folder may contain:

- `JARI_PROTAC_Report.pdf`
- `DeepPK_Predictions.csv`
- `DeepPK_Cleaned_Output.csv`
- `DeepPK_Predictions.json`
- `Protac.svg`
- `Protac.png`
- `category_distribution.png`
- `toxic_safe_distribution.png`
- `metabolism_inhibitor_chart.png`
- `metabolism_substrate_chart.png`
- `deeppk_pipeline.log`

## API Response Shape

`POST /api/deeppk/run` returns:

```json
{
  "success": true,
  "message": "DeepPK report generated successfully.",
  "job_id": "20260519_101955_c89b0c9d",
  "pdf_url": "/api/deeppk/download/<job_id>/JARI_PROTAC_Report.pdf",
  "deeppk": {
    "pdf_url": "/api/deeppk/download/<job_id>/JARI_PROTAC_Report.pdf",
    "csv_url": "/api/deeppk/download/<job_id>/DeepPK_Predictions.csv",
    "clean_csv_url": "/api/deeppk/download/<job_id>/DeepPK_Cleaned_Output.csv",
    "json_url": "/api/deeppk/download/<job_id>/DeepPK_Predictions.json",
    "svg_url": "/api/deeppk/download/<job_id>/Protac.svg",
    "pipeline_log_url": "/api/deeppk/download/<job_id>/deeppk_pipeline.log"
  },
  "rdkit_descriptors": {},
  "warnings": []
}
```

## Dependencies

Runtime Python dependencies required by the restored workflow:

- `rdkit`
- `pandas`
- `requests`
- `rich`
- `Pillow`
- `matplotlib`
- `reportlab`

## Validation

Direct wrapper validation:

- `run_deeppk_pipeline(smiles="CCO")` succeeded

HTTP validation:

- `POST /api/deeppk/run` with `{"smiles":"CCO"}` returned `200`
- returned `pdf_url` and `deeppk.pdf_url`
- `GET /api/deeppk/download/<job_id>/JARI_PROTAC_Report.pdf` returned `200`
- validation PDF size: `2,088,952` bytes

## Known Limitations

- the restored flow depends on the external DeepPK service at the University of Queensland
- upstream latency can make a request take up to the configured wait limit
- current default wait is controlled by `DEEPPK_MAX_WAIT_SECONDS` and defaults to `300`
- the workflow is synchronous today; a future background-job queue would improve UX for long-running requests

## Phase 2.3 Popup + DeepPK UX Polish

- the builder now calls `POST /api/admet/run` first so local RDKit descriptors appear immediately, then calls `POST /api/deeppk/run` for the slower report workflow
- [static/js/protac-admet.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-admet.js) keeps the RDKit table visible during DeepPK work, rotates the button states through `Calculating RDKit…`, `Running DeepPK…`, `Report Ready`, and `DeepPK Retry Available`, and renders inline failures instead of browser alerts
- [templates/partials/_deeppk_loader.html](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/templates/partials/_deeppk_loader.html) and [static/js/protac-loader.js](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/static/js/protac-loader.js) reuse the `view_ligase` loader pattern with rotating helper messages and related-tool links
- [protac_builder/deeppk.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/protac_builder/deeppk.py) now wraps the whole pipeline in stage-aware error handling for:
  - `validate_input`
  - `rdkit_descriptors`
  - `prepare_job_dir`
  - `run_smiles_drug_props`
  - `run_json_analyzer`
  - `run_deeppk_display`
  - `collect_outputs`
  - `response`
- full tracebacks are appended to [logs/deeppk_errors.log](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/logs/deeppk_errors.log), while frontend-safe failures return JSON with `error`, `details`, `stage`, `job_id`, `rdkit_descriptors`, and `retryable`
- the wrapper now sets `MPLCONFIGDIR` per job, and [tools/deeppk/DeepPKDisplay.py](/Users/jxs794/Documents/VLISEMOD/PROTAC_BUILDER/tools/deeppk/DeepPKDisplay.py) now tolerates empty pie-chart datasets so `POST /api/deeppk/run` can complete successfully for small validation molecules like `CCO`
- validation on May 19, 2026:
  - `python -m compileall .` passed
  - `POST /api/admet/run` with `{"smiles":"CCO"}` returned `200`
  - `POST /api/deeppk/run` with `{"smiles":"CCO"}` returned `200`
  - returned files included PDF, CSV, cleaned CSV, JSON, and SVG download URLs

## Phase 2.4 API Docs + Reference Finalization

- `/api-docs` now documents the restored DeepPK flow as active, not future work
- the public docs now distinguish:
  - `POST /api/admet/run` for the fast local RDKit layer
  - `POST /api/deeppk/run` for the slower DeepPK report layer
- successful DeepPK responses are now documented using the public `links` alias as well as the existing `deeppk` file object
- failure docs now explicitly describe the structured JSON error schema returned by the wrapper

## Phase 2.5 Client-Facing API Docs

- `/api-docs` now presents DeepPK as part of a public external-usage workflow:
  - run `POST /api/admet/run` first for fast RDKit descriptors
  - run `POST /api/deeppk/run` second for report files
- browser-facing docs now include Python `requests` and curl examples for DeepPK consumers
- the visible docs page no longer discusses compatibility aliases, while this audit keeps the deeper implementation history
