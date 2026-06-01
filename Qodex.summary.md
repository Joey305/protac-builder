# Qodex.summary

## Task
Fix PROTAC Builder Warhead Hunter / Target Builder remote import handoff.

## Original Goal
Make sure PROTAC Builder can communicate with the backend/RANDY service, see Warhead Hunter job assets, and import target PDB/SDF files without `Backend payload missing detected.target_pdb`.

## Assumptions
- The failing deployed job payload can come from a remote RANDY-style handoff where file refs are provided as `pdb_path` / `sdf_path` / `svg_*_path` instead of frontend-ready `detected.*`.
- Live production-only job IDs were not guaranteed to be available locally, so mocked normalization checks were used alongside local route validation.
- Existing frontend fallback normalization in `static/js/COPYscripts.js` should remain as a defensive fallback, but the backend should now provide a normalized payload directly.

## Files Inspected
- `protac_builder/route_impl.py` — identified the main `/api/warheadhunter/job/<job_id>` and `/api/warheadhunter/job/<job_id>/file/<filename>` implementations and confirmed the raw remote passthrough.
- `protac_builder/warhead_handoff.py` — inspected remote fetch helpers, token handling, and existing filename restrictions.
- `protac_builder/api_routes.py` — confirmed API blueprint aliases for the Warhead Hunter job and file routes.
- `protac_builder/legacy_routes.py` — confirmed legacy `/copy/api/...` aliases for the same job and file routes.
- `static/js/COPYscripts.js` — confirmed the frontend already performs partial normalization from `public_base + options[0]`, and that the thrown error comes from missing `detected.target_pdb`.
- `README.md` — checked current env-var documentation for Warhead Hunter deployment config.
- `Qodex.summary.md` — replaced the previous task summary with this one.

## Files Changed
- `protac_builder/route_impl.py` — added frontend payload normalization, local option enrichment, safe nested file serving, and structured diagnostics.
- `protac_builder/warhead_handoff.py` — added safe relative file-ref validation/extraction and updated remote file proxying to support nested safe paths.
- `protac_builder/api_routes.py` — widened the API file route to `<path:filename>`.
- `protac_builder/legacy_routes.py` — widened the legacy `/copy/api/...` file route to `<path:filename>`.
- `README.md` — added non-secret guidance for remote Warhead Hunter API base and bearer-token env vars.

## Files Created
- `Qodex.summary.md` — documented the root cause, route map, implementation, and validation results for this fix.

## Implementation Summary
The backend now normalizes Warhead Hunter job payloads into one frontend-compatible contract for both local and remote jobs. Remote RANDY-style responses that only expose `pdb_path`, `sdf_path`, or nested `job_files/...` asset refs are converted into normalized `options`, `public_base`, `option_count`, `first_option`, `warhead`, and `detected.target_pdb` / `detected.warhead_sdf` fields. The file-serving route now accepts `<path:filename>`, validates safe relative refs, serves nested local files directly when present, falls back to basename lookup for older flat-cache behavior, and proxies safe nested remote paths through the configured backup API without exposing tokens.

## Key Decisions
- Root cause was confirmed as both a schema mismatch and a path-handling mismatch: remote job payloads were returned mostly raw, and the file route rejected nested safe relative refs used by remote payloads.
- Kept frontend changes out of scope because the backend can now satisfy the existing frontend contract directly, while preserving the defensive fallback already present in `static/js/COPYscripts.js`.
- Normalized local job responses too so remote and local imports share the same response shape and diagnostics.
- Preserved CORS behavior and existing local-source resolution order while adding only safe JSON diagnostics.

## Commands Run
- `rg -n "warheadhunter|target_pdb|warhead_sdf|public_base|pdb_file|sdf_path|pdb_path|fetch_remote_job|fetch_remote_job_file|WARHEAD_HUNTER_JOB_API_BASE" protac_builder/route_impl.py protac_builder/warhead_handoff.py protac_builder/api_routes.py protac_builder/legacy_routes.py static/js/COPYscripts.js README.md Qodex.summary.md` — mapped routes, helpers, env-var docs, and frontend expectations.
- `sed -n '1,260p' protac_builder/route_impl.py` and `sed -n '880,1105p' protac_builder/route_impl.py` — inspected the Warhead Hunter route implementations and local option scanning.
- `sed -n '1,260p' protac_builder/warhead_handoff.py` — inspected remote job/file fetch logic and source resolution.
- `sed -n '1,260p' protac_builder/api_routes.py` — confirmed API blueprint aliases.
- `sed -n '1,260p' protac_builder/legacy_routes.py` — confirmed legacy `/copy/api/...` aliases.
- `sed -n '1930,2065p' static/js/COPYscripts.js` — confirmed frontend fallback normalization and the exact thrown import error path.
- `python -m py_compile app.py protac_builder/route_impl.py protac_builder/warhead_handoff.py protac_builder/api_routes.py protac_builder/legacy_routes.py` — passed.
- `python - <<'PY' ... from app import app; print(app.url_map) ... PY` — passed and confirmed both API and legacy Warhead Hunter routes.
- `python - <<'PY' ... normalize_safe_warhead_file_ref(...) ... PY` — passed allow/block smoke tests for nested safe refs and traversal rejection.
- `python - <<'PY' ... normalize_hunter_payload_for_frontend(...) ... PY` — passed mocked remote-payload normalization and produced `detected`, `public_base`, and normalized `options`.
- `python - <<'PY' ... app.test_client() with patched fetch_remote_job ... PY` — passed route-level smoke test for normalized remote JSON and `400` traversal blocking on the file endpoint.
- `flask --app app routes | grep -i warhead` — passed and confirmed deployed route patterns use `<path:filename>` for API and legacy aliases.

## Validation Results
- Syntax checks passed for `app.py`, `protac_builder/route_impl.py`, `protac_builder/warhead_handoff.py`, `protac_builder/api_routes.py`, and `protac_builder/legacy_routes.py`.
- Flask import and route-map checks passed; `GET /api/warheadhunter/job/<job_id>` is served by `protac_builder.route_impl.warheadhunter_job_index`, and `GET /api/warheadhunter/job/<job_id>/file/<path:filename>` is served by `protac_builder.route_impl.warheadhunter_job_file` through both direct and API-blueprint aliases.
- API blueprint aliases exist in `protac_builder/api_routes.py`, and legacy `/copy/api/...` aliases exist in `protac_builder/legacy_routes.py`.
- Frontend normalization already existed in `static/js/COPYscripts.js`, but it depended on backend-compatible `public_base` and option refs; the backend now provides those consistently.
- Mocked remote normalization produced `detected.target_pdb`, `detected.warhead_sdf`, `public_base`, `option_count`, and normalized option refs as expected.
- Flask test-client smoke checks confirmed `/api/warheadhunter/job/7511ee2d` returns normalized remote JSON under a patched remote payload and that traversal attempts against `/api/warheadhunter/job/7511ee2d/file/job_files/../../secret.json` return structured JSON `400`.
- Safe-path smoke tests allowed `6euc_A_RM0.pdb` and `job_files/WAR_PDB/6euc_A_RM0.pdb`, and rejected `../secret.txt`, `/etc/passwd`, `foo.py`, and `job_files/../../secret.json`.

## Known Issues
- No live deployed remote job fetch was run from this workspace because production-only job availability and matching remote credentials are environment-dependent.
- A full end-to-end browser import test against the deployed UI was not run inside this pass, so final confirmation still depends on post-deploy verification with a known remote job ID.
- If a remote service returns unusable or unsafe file refs, the backend now reports structured diagnostics, but import will still fail correctly rather than fabricating paths.

## Manual Verification
1. Run `curl -s "https://protacbuilder.com/api/warheadhunter/job/10b84b46" | jq .` after deploy.
2. Confirm the response includes `public_base`, `options[0].pdb_file`, `options[0].sdf`, and ideally `detected.target_pdb` plus `detected.warhead_sdf`.
3. Run `curl -I "https://protacbuilder.com/api/warheadhunter/job/10b84b46/file/8wb1_A_W3T_204_plain.svg"` and confirm a `200` response for an existing asset.
4. In the deployed UI, load a known Warhead Hunter job, verify the preview renders, then click confirm import and confirm the builder advances without the missing-`detected.target_pdb` error.

## Suggested Next Prompt
Run a post-deploy verification against a known remote Warhead Hunter job ID and, if needed, capture one real normalized `/api/warheadhunter/job/<job_id>` response so we can verify the frontend import step against production data.
