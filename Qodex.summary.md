# Qodex.summary

## Task
Diagnose and fix remaining live PROTAC Builder E3 PDB handoff failures.

## Original Goal
Resolve continuing production 404s for `/api/e3ligase/pdb/...` after the initial variant-resolution patch, especially VHL `4B9K_TG0_1.pdb` and TRIM21 `7HMA_LV4.pdb`.

## Assumptions
- RANDY’s current E3 API contract remains `GET /backup/e3/healthz`, `GET /backup/e3/ligase-pdbs/<ligase>`, and `GET /backup/e3/file/pdb/<ligase>/<filename>`.
- Public `401` responses from `randy.rove-vernier.ts.net/backup/e3/...` mean RANDY requires bearer auth for listing and file access.
- The Heroku CLI context available from this workspace does not have access to the production app name/config, so config verification had to be inferred from live HTTP behavior rather than direct `heroku config:get`.

## Files Inspected
- `protac_builder/e3_handoff.py` — inspected current base normalization, candidate generation, auth, and file-fetch logic.
- `protac_builder/route_impl.py` — inspected the `/api/e3ligase/pdb/...` wrapper and added the debug route implementation.
- `protac_builder/api_routes.py` — confirmed public route registration and added the debug route registration.
- `static/js/COPYscripts.js` — inspected frontend proxy fallback behavior and added session-scoped 404 suppression.
- `static/data/ligases.json` — confirmed the builder still requests `VHL/4B9K_TG0_1.pdb` and `TRIM21/7HMA_LV4.pdb`.
- `static/data/recruiter_pdb_map.json` — confirmed both filenames are still present in shipped recruiter metadata.
- `README.md` — updated E3 env var and debug-route documentation.
- `.env.example` — added the E3 token placeholder.
- `/Users/jxs794/Downloads/protac-builder-logs-1780529812488.txt` — inspected production logs to compare deployed behavior with current repo code.

## Files Changed
- `protac_builder/e3_handoff.py` — added legacy base-var compatibility, safe upstream diagnostics, per-base listing/fetch inspection, stronger failure logging, and a reusable debug helper.
- `protac_builder/route_impl.py` — added `/api/e3ligase/debug/pdb/<ligase>/<filename>` and preserved clean `400`/`404` handling on the main proxy route.
- `protac_builder/api_routes.py` — registered the debug route.
- `static/js/COPYscripts.js` — added sessionStorage caching of known-missing ligase proxy URLs to avoid repeated 404 spam before falling back to RCSB.
- `README.md` — documented `E3_RANDY_BASE_URL`, `E3_DATA_BASE_URL`, `E3_LIGANDALYZER_BASE_URL`, required auth, and the safe debug endpoint.
- `.env.example` — added `E3_RANDY_TOKEN=`.
- `Qodex.summary.md` — replaced the prior summary with this production-focused incident summary.

## Files Created
- `Qodex.summary.md` — task summary for the live E3 PDB handoff diagnosis/fix.

## Implementation Summary
The live evidence showed this was no longer just a filename-variant issue. Public production requests to:

- `/api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb`
- `/api/e3ligase/pdb/TRIM21/7HMA_LV4.pdb`
- `/api/e3ligase/pdb/VHL/8VLB_3JF.pdb`
- `/api/e3ligase/pdb/TRIM21/7HLP_A34_1.pdb`

all returned the same clean downstream `404`, including filenames that should be “good-looking” metadata entries. At the same time, the two hard-coded fallback hosts still present in `protac_builder/e3_handoff.py`:

- `https://e3ligandalyzer-adb8adfde220.herokuapp.com`
- `https://stan.rove-vernier.ts.net`

both return plain HTML `404` for:

- `/backup/e3/healthz`
- `/backup/e3/ligase-pdbs/VHL`
- `/backup/e3/file/pdb/VHL/8VLB_3JF.pdb`

That proves a real production failure mode: if the app is not reading a valid RANDY base from config, it silently falls through to dead fallback hosts and every ligase PDB request becomes a downstream `404`.

The patch therefore focused on production-proof diagnostics and compatibility:

1. Added support for legacy base env var names:
   - `E3_RANDY_BASE_URL`
   - `E3_DATA_BASE_URL`
   - `E3_LIGANDALYZER_BASE_URL`

   This removes a likely config mismatch where Heroku may already have an older var name set but current code only reads the newer `*_API_BASE` name.

2. Added `inspect_remote_ligase_pdb()` and the safe route:
   - `GET /api/e3ligase/debug/pdb/<ligase>/<filename>`

   It returns safe diagnostics only: normalized host/path, which env-var names were present, whether the app is running in fallback-only mode, listing status/count, matched filename, and per-candidate fetch statuses.

3. Preserved the main `/api/e3ligase/pdb/...` route behavior, but now its logs include enough structured context to distinguish:
   - fallback-only config mistakes,
   - listing failures,
   - auth failures,
   - true remote not-found cases.

4. Added session-scoped frontend caching of proxy `404`s so the browser does not keep hammering the same missing ligase proxy URL before falling back to RCSB.

## Key Decisions
- Did not rewrite the proxy architecture. The main route still proxies through the same builder API path.
- Did not remove hard-coded fallback bases yet, because the request explicitly said to preserve fallback behavior unless it was proven wrong. Instead, the debug route now makes fallback-only operation visible.
- Added compatibility for old base env names rather than assuming production had already migrated to `E3_RANDY_API_BASE`.
- Kept the debug endpoint safe for production by exposing only host/path, filename, counts, and status codes, never raw env values or tokens.
- Did not rewrite `static/data/ligases.json` yet, because live evidence showed even “likely good” filenames were failing; that points to upstream selection/config first, not just two stale records.

## Commands Run
- `rg -n "e3_handoff|e3ligase|ligase-pdbs|file/pdb|backup/e3|E3_RANDY|RANDY|E3_.*BASE|Authorization|Bearer|4B9K_TG0|7HMA_LV4|VHL|TRIM21|recruiter_pdb_map|ligases.json|all upstream bases returned 404" .` — mapped route ownership, env vars, hard-coded fallbacks, auth handling, and metadata references.
- `sed -n '1,280p' protac_builder/e3_handoff.py` — inspected current handoff helper.
- `sed -n '1400,1535p' protac_builder/route_impl.py` — inspected current E3 proxy wrapper.
- `sed -n '1,220p' protac_builder/api_routes.py` — confirmed public route registration.
- `sed -n '1,220p' /Users/jxs794/Downloads/protac-builder-logs-1780529812488.txt` — confirmed the older production log message was still present in the saved log snapshot.
- `curl -sS -D - https://protacbuilder.com/api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb ...` — live check returned clean JSON `404`.
- `curl -sS -D - https://protacbuilder.com/api/e3ligase/pdb/TRIM21/7HMA_LV4.pdb ...` — live check returned clean JSON `404`.
- `curl -sS -D - https://protacbuilder.com/api/e3ligase/pdb/VHL/8VLB_3JF.pdb ...` — live check returned clean JSON `404`.
- `curl -sS -D - https://protacbuilder.com/api/e3ligase/pdb/TRIM21/7HLP_A34_1.pdb ...` — live check returned clean JSON `404`.
- `curl -sS -D - https://randy.rove-vernier.ts.net/backup/e3/healthz ...` — returned `401`, proving RANDY requires auth.
- `curl -sS -D - https://randy.rove-vernier.ts.net/backup/e3/ligase-pdbs/VHL ...` — returned `401`, proving listing requires auth.
- `curl ... https://e3ligandalyzer-adb8adfde220.herokuapp.com/backup/e3/...` and `curl ... https://stan.rove-vernier.ts.net/backup/e3/...` — both fallback hosts returned HTML `404` for health, listing, and file paths.
- `python - <<'PY' ... bool(os.environ.get(...)) ... PY` — confirmed this local workspace does not have E3 base/token env vars set.
- `python - <<'PY' ... recruiter_pdb_map.json ... PY` — confirmed `4B9K_TG0_1.pdb` and `7HMA_LV4.pdb` are still present in local recruiter metadata.
- `python -m py_compile app.py protac_builder/e3_handoff.py protac_builder/route_impl.py protac_builder/api_routes.py` — passed.
- `node --check static/js/COPYscripts.js` — passed.
- `python - <<'PY' ... mocked Flask test client with E3_RANDY_BASE_URL ... PY` — passed exact match, variant fallback, TRIM21 exact match, missing-file `404`, traversal `400`, and debug-route validation.
- `python - <<'PY' ... mocked Flask test client with no E3 env vars ... PY` — passed and showed `used_fallback_only: true` plus only hard-coded dead bases in the debug payload.

## Validation Results
- Syntax validation passed for all modified Python files.
- Frontend syntax validation passed for `static/js/COPYscripts.js`.
- Mocked route validation passed:
  - `GET /api/e3ligase/pdb/VHL/8VLB_3JF.pdb` -> `200`
  - `GET /api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb` -> resolved to `4B9K_TG0.pdb` and returned `200`
  - `GET /api/e3ligase/pdb/TRIM21/7HMA_LV4.pdb` -> `200`
  - `GET /api/e3ligase/pdb/VHL/DOES_NOT_EXIST.pdb` -> clean `404`
  - `GET /api/e3ligase/pdb/VHL/../secret.pdb` -> `400`
- Mocked debug-route validation passed and showed:
  - legacy env var detection (`E3_RANDY_BASE_URL`)
  - normalized `/backup/e3` base path
  - listing status/count
  - matched filename (`4B9K_TG0.pdb`)
  - source (`randy-listing`)
- Live production validation showed:
  - the public builder route is now returning the newer clean JSON `404` shape,
  - but even “good-looking” filenames return `404`,
  - which makes pure stale-metadata explanation unlikely.
- Live fallback-host validation showed both hard-coded fallback hosts are dead for the RANDY `/backup/e3` contract.
- Direct Heroku config inspection could not be run from this workspace because `heroku apps:info -a protacbuilder` returned “app not found,” so exact production env names/values remain to be verified after deploy.

## Known Issues
- The exact live Heroku app name and config access were unavailable here, so I could not directly confirm whether production currently sets:
  - `E3_RANDY_API_BASE`
  - `E3_RANDY_BASE_URL`
  - `E3_RANDY_TOKEN`
  - or related legacy vars.
- Because RANDY requires auth and no token is available in this workspace, I could not query the live RANDY listing inventory directly for `4B9K_TG0_1.pdb` or `7HMA_LV4.pdb`.
- Public production still needs one deploy using this updated repo before the new `/api/e3ligase/debug/pdb/...` route can prove the exact live per-base statuses.

## Manual Verification
1. Test `/api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb`.
2. Test `/api/e3ligase/pdb/TRIM21/7HMA_LV4.pdb`.
3. Open a builder session imported from E3 Ligandalyzer.
4. Confirm E3 PDB loading succeeds or fails with a clean, accurate message.
5. Confirm existing builder molecule editing and PROTAC generation still work.

## Suggested Next Prompt
After deploying this branch, call `/api/e3ligase/debug/pdb/VHL/4B9K_TG0_1.pdb` and `/api/e3ligase/debug/pdb/TRIM21/7HMA_LV4.pdb`, then use the returned `normalized_bases`, `configured_env_vars`, and `direct_fetch_statuses` to set the exact Heroku `E3_RANDY_API_BASE` and token vars or confirm true RANDY data gaps.
