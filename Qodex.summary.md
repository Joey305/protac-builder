# Qodex.summary

## Task
Make Warhead Hunter / Target Builder import remote-only through RANDY.

## Original Goal
Stop PROTAC Builder from checking local job directories for Target Builder import and make RANDY the exclusive source of truth for job lookup and file handoff.

## Assumptions
- RANDY is the canonical backend for Target Builder / Warhead Hunter job discovery and asset handoff.
- Local directories such as `static/hunter_jobs` and `uploads/warhead_hunter_imports` may still exist on disk, but they must not decide whether `/api/warheadhunter/job/<job_id>` succeeds.
- In this workspace, `WARHEAD_HUNTER_JOB_API_BASE` is not configured, so local runtime tests can validate remote-only diagnostics but not live remote success.

## Files Inspected
- `protac_builder/route_impl.py` — traced `warheadhunter_job_index()` and found the old `resolve_job_dir()` gate plus the local-directory error message.
- `protac_builder/warhead_handoff.py` — inspected remote fetch helpers, cache behavior, and old local-source helpers.
- `protac_builder/api_routes.py` — confirmed `/api/warheadhunter/job/<job_id>` and the file proxy routes remain registered.
- `protac_builder/legacy_routes.py` — confirmed legacy `/copy/api/...` aliases remain registered.
- `static/js/COPYscripts.js` — checked how frontend messaging and selected-option flow respond to backend diagnostics.
- `templates/builder.html` — confirmed multi-option selector UI remained available for both Target Builder and Warhead Hunter flows.
- `README.md` — updated deployment guidance to describe remote-only import discovery.
- `Qodex.summary.md` — replaced the previous mixed local/remote summary with this remote-only one.

## Files Changed
- `protac_builder/route_impl.py` — removed local lookup from `warheadhunter_job_index()`, added remote-only `?debug=1` diagnostics, added remote-only missing-payload behavior, preserved multi-option normalization, and switched file serving to remote proxy plus optional remote cache only.
- `protac_builder/warhead_handoff.py` — removed local-discovery diagnostics from the import response path and updated the default missing-job payload to remote-only wording.
- `static/js/COPYscripts.js` — changed user-facing error messages to remote-only explanations and kept console logging of safe diagnostics.
- `README.md` — documented that Target Builder / Warhead Hunter import now uses `WARHEAD_HUNTER_JOB_API_BASE` as the exclusive job-discovery authority.
- `Qodex.summary.md` — documented the remote-only design, validation, and limitations.

## Files Created
- `Qodex.summary.md` — task summary for the remote-only RANDY import change.

## Implementation Summary
`/api/warheadhunter/job/<job_id>` is still implemented in `protac_builder.route_impl.warheadhunter_job_index()`, but it no longer calls `resolve_job_dir()` or scans local job folders before contacting RANDY. The route now always uses `fetch_remote_job_diagnostics(job_id)` as the source of truth. If RANDY is not configured, the route returns a structured `503` JSON response explaining that remote handoff is not configured. If RANDY returns `404`, the route returns a structured `404` JSON response explaining that RANDY did not find the job ID. If RANDY returns a payload, the route normalizes all candidate options, preserves multi-ligand choices, and only succeeds when at least one option includes importable PDB and SDF references.

The file route still uses `/api/warheadhunter/job/<job_id>/file/<path:filename>`, but it no longer discovers jobs from local folders. It optionally serves a previously cached remote file from `uploads/warhead_hunter_imports/<job_id>` if present and safe; otherwise it proxies the request to RANDY and writes the fetched file into that cache directory. Cache files are now an optimization only, not an authority for job existence.

After inspecting the live `47772fd7` payload, normalization was tightened further so that when RANDY provides explicit job-root artifact files, only those top-level handoff files are turned into import options. That prevents PROTAC Builder from rendering the entire internal `job_files/MCS_Output/...` universe and limits the UI to the curated root deliverables that were actually meant to be handed off.

## Key Decisions
- Removed the `resolve_job_dir()` branch from `warheadhunter_job_index()` so stale local directories can never shadow valid remote jobs.
- Kept `_scan_hunter_job_dir()` and other local helpers on disk for safety, but they are no longer used by the import lookup route.
- Added `source_policy: remote_only` and `local_lookup: disabled` to both success and debug/failure payloads so the frontend and operators can see the policy clearly.
- Treated SMILES-only RANDY payloads as a distinct structured failure: the route now reports that PDB/SDF files are required instead of trying to fabricate structure files.
- Preserved explicit multi-ligand selection by returning all valid options and `requires_selection: true` with `selected_option_id: null` when more than one valid option exists.
- Preferred RANDY `files` entries with `root == "job"` and direct job-root artifact filenames over the much larger remote `options` array whenever that curated top-level handoff set exists.

## Commands Run
- `rg -n "warheadhunter_job_index|resolve_job_dir|_scan_hunter_job_dir|fetch_remote_job|fetch_remote_job_diagnostics|fetch_remote_job_file|missing_job_payload|A local job directory was found|No valid warhead options found|TARGET_BUILDER_JOBS_DIR|WARHEAD_HUNTER_JOBS_DIR|HUNTER_JOBS_DIR|WARHEAD_HUNTER_IMPORTS_DIR|pdb_path|sdf_path|target_pdb|warhead_sdf|requires_selection|selectedOption" ...` — mapped local-vs-remote flow and confirmed where old local behavior lived.
- `python -m py_compile app.py protac_builder/route_impl.py protac_builder/warhead_handoff.py protac_builder/api_routes.py protac_builder/legacy_routes.py` — passed.
- `flask --app app routes | grep -i warhead` — passed and confirmed the public and legacy Warhead Hunter routes still exist.
- `node --check static/js/COPYscripts.js` — passed.
- `python - <<'PY' ... client.get('/api/warheadhunter/job/47772fd7?debug=1') ... PY` — passed and confirmed remote-only debug JSON with `source_policy: remote_only` and `local_lookup: disabled`.
- `python - <<'PY' ... patched fetch_remote_job_diagnostics(remote success) ... PY` — passed and confirmed normalized remote success with `valid_option_count = 1` and `detected.*`.
- `python - <<'PY' ... patched fetch_remote_job_diagnostics(remote multi-option) ... PY` — passed and confirmed `valid_option_count = 2`, `requires_selection = true`, and `selected_option_id = null`.
- `python - <<'PY' ... patched fetch_remote_job_diagnostics(smiles-only payload) ... PY` — passed and confirmed `status = remote_payload_missing_structure_files`.
- `python - <<'PY' ... normalize_safe_warhead_file_ref(...) ... PY` — passed allowed and blocked path tests.
- `python - <<'PY' ... client.get('/api/warhunter/job/7511ee2d/file/job_files/../../secret.json') ... PY` — adapted to the real route and confirmed traversal blocking with structured `400` JSON.
- `python - <<'PY' ... client.get('/api/warheadhunter/job/47772fd7') ... PY` — passed and confirmed the non-debug response now reports remote-not-configured `503` instead of local-directory findings.
- `rg -n "resolve_job_dir|_scan_hunter_job_dir" protac_builder/route_impl.py` — confirmed `_scan_hunter_job_dir()` remains only as a helper definition and `resolve_job_dir` is no longer referenced from the route file.
- `curl -s 'https://protacbuilder.com/api/warheadhunter/job/47772fd7?debug=1' | python -m json.tool` — showed live remote payload metadata with `option_count: 462` and `valid_option_count: 154` before curated filtering.
- `curl -s 'https://protacbuilder.com/api/warheadhunter/job/47772fd7' > /tmp/job47772fd7.json` plus targeted Python inspection — confirmed the remote payload includes both internal `job_files/...` artifacts and top-level `root: "job"` handoff files.
- `python - <<'PY' ... normalize_hunter_payload_for_frontend('47772fd7', live_payload) ... PY` — passed and confirmed curated filtering reduces the job to exactly two valid top-level options.
- `python - <<'PY' ... patched fetch_remote_job_diagnostics(live 47772fd7 payload) ... PY` — passed and confirmed route-level output now returns exactly the intended two options for this job.

## Validation Results
- `GET /api/warheadhunter/job/<job_id>` remains implemented in `protac_builder.route_impl.warheadhunter_job_index()`.
- Local directory lookup currently no longer occurs in `warheadhunter_job_index()`; `resolve_job_dir` is not referenced there anymore.
- Remote RANDY lookup now occurs unconditionally through `fetch_remote_job_diagnostics(job_id)` in the canonical job route.
- The old local-directory-specific error path (`A local job directory was found, but no option contained importable warhead files.`) was removed from the import route and is no longer surfaced to the frontend.
- The frontend does not assume local-vs-remote behavior; it now consumes remote-only diagnostics and still drives selection/import from normalized option objects.
- Remote-not-configured debug response passed: `source_policy = remote_only`, `local_lookup = disabled`, and `remote.configured = false`.
- Mock remote success passed: `status = 200`, `valid_option_count = 1`, and `detected.target_pdb` / `detected.warhead_sdf` exist.
- Mock remote multi-option passed: `valid_option_count = 2`, `requires_selection = true`, and `selected_option_id = null`.
- Mock SMILES-only payload passed: structured `502` with `status = remote_payload_missing_structure_files`.
- Secure file-path validation passed for both allowed and blocked paths.
- Live `47772fd7` payload inspection showed RANDY was returning a huge internal candidate universe, but the updated normalization now filters that payload to the top-level handoff artifacts only.
- Live-payload normalization for `47772fd7` now returns exactly two valid options: `4HHZ chain C ligand 15S resid 401` and `9DMC chain A ligand APR resid 1102`.

## Known Issues
- Live deployed verification against a real RANDY job ID could not be run from this workspace because `WARHEAD_HUNTER_JOB_API_BASE` is not configured locally and production credentials are not available here.
- Manual browser verification of the updated remote-only messages and option selector was not run in a live browser session during this pass.
- `_scan_hunter_job_dir()` still exists as a helper in `route_impl.py`; it is no longer used by the import route, but it was not deleted in this change.

## Manual Verification
1. Call `GET /api/warheadhunter/job/<job_id>?debug=1` on a deployed environment.
2. Confirm the JSON includes `source_policy: remote_only`, `local_lookup: disabled`, and only remote diagnostics.
3. Test a known valid RANDY job ID and confirm the response includes normalized options and no local-directory language.
4. Test a RANDY 404 job ID and confirm the response says `RANDY did not find this job ID.`
5. In the browser, load a multi-option job and confirm the user must explicitly click a ligand option before import.
6. For job `47772fd7`, confirm the selector shows only the two top-level options from the job root rather than dozens of internal MCS candidates.

## Suggested Next Prompt
Run deployed `?debug=1` checks against one valid RANDY job and one missing RANDY job so we can confirm the production environment variables and remote token wiring are correct.
