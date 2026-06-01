# Qodex.summary

## Task
Fix multi-ligand Target Builder import selection and diagnose Warhead Hunter job 404/no-options failures.

## Original Goal
Allow PROTAC Builder to load Warhead Hunter / Target Builder jobs, display multiple ligand candidates, let the user select the correct one, and fix the `No valid warhead options found` error caused by `/api/warheadhunter/job/<job_id>` returning 404.

## Assumptions
- Job `47772fd7` is expected to be a remote Warhead Hunter / Target Builder job rather than a local development fixture.
- In this local workspace, a missing `WARHEAD_HUNTER_JOB_API_BASE` means no remote RANDY lookup can occur, so the reproduced 404 here comes from PROTAC Builder itself.
- Frontend fallback compatibility for `data.detected.target_pdb` and `data.detected.warhead_sdf` still matters, even when the user must explicitly choose among multiple options.

## Files Inspected
- `protac_builder/route_impl.py` — traced `GET /api/warheadhunter/job/<job_id>` and confirmed `warheadhunter_job_index()` was returning the JSON 404.
- `protac_builder/warhead_handoff.py` — checked whether remote API configuration existed and whether a remote fetch was attempted.
- `protac_builder/api_routes.py` — confirmed `/api/warheadhunter/job/<job_id>` is registered and routed to `route_impl`.
- `protac_builder/legacy_routes.py` — confirmed legacy `/copy/api/...` aliases still exist.
- `static/js/COPYscripts.js` — confirmed the frontend assumed `options[0]` in both preview and confirm-import logic.
- `templates/builder.html` — inspected Target Builder Import and Warhead Hunter import UI containers, including the pre-existing `hunter-ligand-options` slot.
- `README.md` — reviewed current remote Warhead Hunter deployment configuration notes.
- `Qodex.summary.md` — replaced the previous handoff-only summary with this task-specific summary.

## Files Changed
- `protac_builder/warhead_handoff.py` — added remote job diagnostics so the backend can report whether remote lookup was configured, attempted, and what status the remote service returned.
- `protac_builder/route_impl.py` — added structured missing-job diagnostics, multi-option normalization, option labels/IDs/URLs, and explicit `requires_selection` behavior.
- `static/js/COPYscripts.js` — replaced `options[0]` assumptions with explicit option rendering, selection state, preview updates, and safer error messaging.
- `templates/builder.html` — added Target Builder option cards, preview panel, hidden debug payload nodes, and disabled confirm buttons that activate only after valid selection.

## Files Created
- `Qodex.summary.md` — documented the diagnosis, implementation, and validation for the multi-ligand + 404 diagnostics fix.

## Implementation Summary
The backend now distinguishes between three different job-load outcomes: local hit, remote hit, and structured miss/diagnostic. For missing jobs, the JSON response now reports safe fields such as `status`, `remote_configured`, `remote_attempted`, `remote_status_code`, `remote_error`, `option_count`, and `debug_hint`, so the frontend can explain whether the backend itself could not find the job locally, whether RANDY was never queried because remote config was missing, or whether the remote service returned 404.

For successful jobs, all normalized warhead options are preserved. Each option now includes a stable `option_id`, human-readable `label`, `preview_url`, `target_pdb_url`, `warhead_sdf_url`, `is_valid`, and `invalid_reason`. The frontend renders all options, auto-selects only when there is exactly one valid option, requires explicit selection when multiple valid options exist, stores the chosen option in the import state, and updates `data.detected` from the selected option so the existing import contract still works.

## Key Decisions
- Kept `/api/warheadhunter/job/<job_id>` as the canonical route and fixed diagnostics there instead of inventing a parallel debug endpoint.
- Treated the reproduced `47772fd7` failure in this workspace as a PROTAC Builder 404, because `WARHEAD_HUNTER_JOB_API_BASE` is not configured locally and the remote RANDY API is therefore not contacted here.
- Returned `requires_selection: true` with `selected_option_id: null` for multi-option jobs so the UI cannot silently fall back to the first ligand.
- Preserved `detected.target_pdb` / `detected.warhead_sdf` compatibility by updating those fields from the selected option during frontend import.

## Commands Run
- `rg -n "warheadhunter|Target Builder Import|No valid warhead options found|detected.target_pdb|warhead_sdf|public_base|options|option_count|selectedOption|LOAD JOB|CONFIRM IMPORT|fetch_remote_job|missing_job_payload|WARHEAD_HUNTER_JOB_API_BASE" ...` — mapped the backend route chain, UI assumptions, and diagnostic hooks.
- `python - <<'PY' from protac_builder.warhead_handoff import _remote_base ... PY` — confirmed `WARHEAD_HUNTER_JOB_API_BASE` is not configured in this workspace.
- `python - <<'PY' from app import app; client.get('/api/warheadhunter/job/47772fd7') ... PY` — reproduced the current JSON 404 and confirmed it came from PROTAC Builder.
- `python -m py_compile app.py protac_builder/route_impl.py protac_builder/warhead_handoff.py protac_builder/api_routes.py protac_builder/legacy_routes.py` — passed.
- `flask --app app routes | grep -i warhead` — passed and confirmed the job/file routes plus legacy aliases.
- `node --check static/js/COPYscripts.js` — passed.
- `python - <<'PY' ... normalize_hunter_payload_for_frontend(one-option payload) ... PY` — passed and confirmed option URLs plus `detected`.
- `python - <<'PY' ... normalize_hunter_payload_for_frontend(multi-option payload) ... PY` — passed and confirmed two preserved options with labels and `requires_selection: true`.
- `python - <<'PY' ... patched fetch_remote_job_diagnostics(remote 404) ... PY` — passed and confirmed structured JSON 404 with safe remote diagnostics.
- `python - <<'PY' ... patched fetch_remote_job_diagnostics(remote multi-option payload) ... PY` — passed and confirmed route-level multi-option normalization.

## Validation Results
- `GET /api/warheadhunter/job/<job_id>` is registered and handled by `protac_builder.route_impl.warheadhunter_job_index`.
- The current 404 for `47772fd7` in this workspace came from PROTAC Builder, not Flask route registration and not RANDY, because remote API configuration is absent locally.
- Remote API lookup is only attempted when `WARHEAD_HUNTER_JOB_API_BASE` is configured; this is now surfaced explicitly in JSON diagnostics.
- The frontend previously assumed `options[0]` in `_loadJobGeneric()` and `_confirmImportGeneric()` inside `static/js/COPYscripts.js`; that assumption has been removed.
- One-option normalization checks passed: `option_count = 1`, option URLs exist, and `detected.target_pdb` / `detected.warhead_sdf` are present.
- Multi-option normalization checks passed: `option_count = 2`, both options are preserved with labels and URLs, and `requires_selection = true` with `selected_option_id = null`.
- Missing-job diagnostics checks passed for both “remote not configured” and mocked “remote 404” cases.
- JS syntax, Python syntax, and route registration checks all passed.

## Known Issues
- No live deployed remote query for `47772fd7` was run from this workspace because production-only remote availability and credentials are environment-dependent.
- Manual browser verification of the updated selector UI was not run inside a live browser session in this pass.
- If a remote payload contains only unusable options, the backend now reports that precisely, but the user will still need a corrected remote job payload before import can succeed.

## Manual Verification
1. Open PROTAC Builder and enter a job ID that returns exactly one valid option.
2. Click `Load Job → Preview` and confirm the option auto-selects, the preview appears, and the confirm button is enabled.
3. Enter a job ID with multiple valid options and confirm the preview panel stays gated until one option is clicked.
4. Click a non-default ligand option and confirm import uses that option’s `target_pdb_url` and `warhead_sdf_url`, not the first option in the array.
5. Test an invalid or missing job and confirm the status message explains whether the backend checked local sources only or also received a remote 404.

## Suggested Next Prompt
Run a deployed verification for job `47772fd7` and capture the normalized JSON response so we can confirm whether production is missing remote configuration, receiving a true RANDY 404, or getting a payload that still lacks valid options.
