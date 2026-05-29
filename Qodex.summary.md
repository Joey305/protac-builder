# Qodex.summary

## Task
Runtime persistence, Warhead Hunter online handoff, and DeepPK diagnostics.

## Original Goal
Fix PROTAC Builder logging so CSV/JSON usage data persists long-term and is not overwritten by Git pushes, fix Warhead Hunter / Target Builder online job import so PROTAC Builder can retain and load imported warhead job information, and debug DeepPK failures that return an HTML Application Error while preserving RDKit descriptor fallback.

## Assumptions
- `d02e20ab` is an online Warhead Hunter / Target Builder job and is not expected to exist locally.
- `static/data` should keep seed/reference assets trackable, but mutable runtime CSVs should not be Git-tracked.
- A full Redis/Celery background queue is out of scope for this pass.

## Files Inspected
- `protac_builder/paths.py` — mutable CSV path definitions.
- `protac_builder/io_utils.py` — CSV initialization and append helpers.
- `protac_builder/usage.py` — usage seed and counter logic.
- `protac_builder/route_impl.py` — Warhead Hunter lookup and builder route logging.
- `protac_builder/api_routes.py` and `protac_builder/legacy_routes.py` — public API and legacy aliases.
- `protac_builder/deeppk.py` and `tools/deeppk/SmilesDrugProps.py` — DeepPK pipeline timeout/error behavior.
- `static/js/COPYscripts.js` and `static/js/protac-admet.js` — Target Builder import and DeepPK frontend parsing.
- `.gitignore` and `README.md` — runtime storage and deployment guidance.

## Files Changed
- `.gitignore` — ignores mutable static CSVs and new runtime/cache directories.
- `README.md` — documents persistence, Warhead handoff env vars, DeepPK timeout behavior, and safe untracking commands.
- `app.py` — adds JSON fallback handling for ADMET/DeepPK API exceptions.
- `protac_builder/paths.py` — centralizes runtime data and Warhead import cache paths.
- `protac_builder/io_utils.py` — migrates legacy static runtime CSVs into runtime storage before initialization.
- `protac_builder/usage.py` — reads verified static seed data and counts new successful runtime usage rows without double-counting copied legacy logs.
- `protac_builder/route_impl.py` — uses robust Warhead job resolution, same-origin job file serving, manifest fallback scanning, and single batch/CLI usage logging.
- `protac_builder/api_routes.py` and `protac_builder/legacy_routes.py` — preserve aliases and expose Warhead job file routes.
- `protac_builder/deeppk.py` — makes DeepPK synchronous timeouts request-safe and logs subprocess timeouts.
- `static/js/COPYscripts.js` — handles non-JSON handoff failures and remote/same-origin import URLs.
- `static/js/protac-admet.js` — avoids dumping platform HTML into the DeepPK UI.
- `tools/deeppk/SmilesDrugProps.py` — adds curl/subprocess timeouts and HTML response detection.
- `static/data/protac_builder_usage_seed.json` — updated to the verified local legacy seed count.

## Files Created
- `protac_builder/warhead_handoff.py` — central Warhead Hunter / Target Builder job ID validation, source lookup, remote fetch, cache helpers, and safe missing-job payloads.
- `uploads/runtime_data/.gitkeep` — keeps the ignored runtime data directory present.
- `uploads/warhead_hunter_imports/.gitkeep` — keeps the ignored Warhead import cache directory present.

## Implementation Summary
Mutable runtime logs now resolve to `PROTAC_RUNTIME_DATA_DIR` or `uploads/runtime_data`, with one-time copy migration from old `static/data` files. Warhead job import now checks configured deployed sources, runtime cache, local dev fallback, and optional remote API handoff, returning safe JSON diagnostics when missing. DeepPK remains RDKit-first, but synchronous report generation now has safer defaults, structured app-level failures, and frontend protection against platform HTML pages.

## Key Decisions
- Kept seed/reference files under `static/data` trackable and ignored only known mutable runtime CSVs.
- Used same-origin `/api/warheadhunter/job/<job_id>/file/<filename>` URLs so imported PDB/SDF/SVG files can be fetched from configured storage without exposing private paths.
- Did not implement a heavy background queue; instead DeepPK now fails gracefully within a request-safe timeout.

## Commands Run
- `pwd` — confirmed project root.
- `git status --short` — found pre-existing `Procfile` deletion and `protac_builder/deeppk.py` modification.
- Required grep searches — mapped runtime CSV, Warhead handoff, and DeepPK references.
- `git ls-files | grep -E 'static/data/(Generated_PROTACs|PROTAC_log|protac_api_downloads|protac_builder_usage)\.csv'` — confirmed mutable CSVs were tracked.
- `git rm --cached ...` — untracked mutable CSVs without deleting local files.
- `python -m compileall app.py protac_builder tools/deeppk` — passed.
- `python -m pytest` — failed because `pytest` is not installed.
- Targeted Flask test-client checks — validated Warhead JSON errors, local fallback job load, ADMET descriptors, and DeepPK JSON response shape.
- Runtime and `git check-ignore` checks — confirmed runtime dirs exist and mutable CSV/cache paths are ignored.

## Validation Results
- Compile passed.
- `pytest` could not run: `No module named pytest`.
- `/api/warheadhunter/job/d02e20ab` returned JSON 404 with deployment guidance locally.
- `/api/warheadhunter/job/../../bad` returned JSON 400.
- `/api/warheadhunter/job/406167aa` returned JSON 200 via local development fallback.
- `/api/admet/run` with `CCO` returned successful RDKit descriptors.
- `/api/deeppk/run` with `CCO` and the provided large PROTAC SMILES returned structured JSON successfully in local low-timeout checks.
- Git ignore checks passed for mutable static CSVs and new runtime/cache paths.

## Known Issues
- `d02e20ab` could not be validated locally because it is an online job, not a local fixture.
- Production must configure shared Warhead storage or `WARHEAD_HUNTER_JOB_API_BASE`; a redirect with only a job ID is insufficient unless PROTAC Builder can retrieve that job from deployed storage/API.
- Existing platform logs are still needed to prove whether the observed hosted HTML Application Error was a request timeout, dyno crash, memory issue, or reverse-proxy platform error.
- `Procfile` was already deleted before this pass and was not restored.

## Manual Verification
1. Start the Flask app and open `/builder`.
2. Enter an invalid Target Builder job ID and confirm a short JSON-derived error appears.
3. Configure deployed Warhead shared storage/API, enter a real online job ID, and confirm preview/import continues to E3 ligase selection.
4. Generate a PROTAC and confirm CSV rows append under `PROTAC_RUNTIME_DATA_DIR` or `uploads/runtime_data`.
5. Run molecular parameters and confirm RDKit descriptors remain visible if DeepPK retries or fails.

## Suggested Next Prompt
Validate the deployed Heroku environment variables and platform logs for Warhead Hunter job `d02e20ab` and the DeepPK HTML Application Error, then decide whether DeepPK should move to a background worker.
