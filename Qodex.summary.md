# Qodex.summary

## Task
Fix PROTAC Builder E3 PDB handoff variant resolution.

## Original Goal
Fix the PROTAC Builder/RANDY communication issue where `/api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb` returns 404 because the handoff route cannot resolve the requested PDB filename upstream.

## Assumptions
- RANDY’s current E3 contract is the source of truth: `/backup/e3/ligase-pdbs/<ligase>` and `/backup/e3/file/pdb/<ligase>/<filename>`.
- `static/data/ligases.json` may contain stale-but-safe recruiter filenames such as `4B9K_TG0_1.pdb`, so the proxy should resolve variants instead of requiring a metadata rewrite.
- Local validation in this workspace can mock the route behavior, but live RANDY verification depends on production-accessible config and token wiring that are not available here.

## Files Inspected
- `protac_builder/api_routes.py` — confirmed `/api/e3ligase/pdb/<ligase>/<path:filename>` is registered here and delegates into route implementation.
- `protac_builder/route_impl.py` — inspected the Flask route wrapper and its current error handling.
- `protac_builder/e3_handoff.py` — found the failing proxy logic and the `all upstream bases returned 404` log message.
- `RANDY/e3_data_routes.py` — verified the live RANDY E3 contract and its own variant-aware file lookup behavior.
- `static/data/ligases.json` — confirmed the builder metadata still references `4B9K_TG0_1.pdb` for VHL.
- `static/js/COPYscripts.js` — checked how the frontend builds the PDB URL and how it behaves when the proxy returns a non-OK response.
- `README.md` — updated E3 proxy env var guidance and base normalization expectations.
- `.env.example` — added the preferred E3 API base env var placeholder.

## Files Changed
- `protac_builder/e3_handoff.py` — added E3 base normalization, safe filename validation, RANDY listing lookup, short TTL cache, variant candidate fallback, and safer structured logging.
- `protac_builder/route_impl.py` — added explicit `400` handling for invalid ligase/PDB requests and clean `404` JSON for missing upstream PDBs.
- `README.md` — documented `E3_RANDY_API_BASE`, accepted legacy E3 base vars, and the normalized `/backup/e3` contract.
- `.env.example` — added `E3_RANDY_API_BASE=`.
- `Qodex.summary.md` — replaced the prior summary with this task summary.

## Files Created
- `Qodex.summary.md` — task summary for the E3 PDB handoff fix.

## Implementation Summary
The root cause was in `protac_builder/e3_handoff.py`. The builder proxy always took whatever base URL it had, blindly appended `backup/e3/file/pdb/<ligase>/<filename>`, and requested the exact filename from `static/data/ligases.json`. That meant a request such as `4B9K_TG0_1.pdb` failed whenever RANDY only exposed `4B9K_TG0.pdb` or another compatible variant, even though the ligase data itself was present upstream.

The fix keeps the same builder route and multi-base fallback pattern, but makes the proxy smarter. It now normalizes each configured base to exactly one `/backup/e3` suffix, ignores non-URL values such as `static/converted_sessions`, calls RANDY’s `GET /backup/e3/ligase-pdbs/<ligase>` endpoint first, and resolves the requested filename case-insensitively against the real remote inventory. If there is no exact match, it strips a trailing numeric variant suffix and tries safe ordered candidates such as `4B9K_TG0_1.pdb`, `4B9K_TG0.pdb`, `4B9K_TG0_2.pdb`, and so on before returning a clean downstream `404`.

## Key Decisions
- Preserved the existing route shape `/api/e3ligase/pdb/<ligase>/<filename>` so the frontend does not need to change.
- Preserved multi-upstream fallback behavior, but normalized every base to the RANDY `/backup/e3` contract instead of concatenating path fragments ad hoc.
- Preferred real RANDY inventory via `/ligase-pdbs/<ligase>` over speculative file fetches, because that lets stale builder metadata resolve safely to exact upstream filenames.
- Kept cache correctness optional by using a short in-memory listing TTL only as an optimization.
- Left `static/data/ligases.json` unchanged for now because the proxy can safely resolve stale `_1` filenames without broad metadata churn.

## Commands Run
- `rg -n "e3_handoff|e3ligase|ligase-pdbs|file/pdb|backup/e3|4B9K|TG0|VHL|upstream bases|RANDY|E3_RANDY|E3.*BASE|ligases.json|builder\\?session|session=" .` — located the route, handoff helper, RANDY contract, and VHL metadata references.
- `rg -n "api/e3ligase|def .*e3|e3_handoff|pdb/<|file/pdb|ligase-pdbs" .` — confirmed the exact builder and RANDY route definitions.
- `rg -n "4B9K|TG0|VHL" static templates .` — confirmed `static/data/ligases.json` references `4B9K_TG0_1.pdb`.
- `sed -n '1,260p' protac_builder/e3_handoff.py` — inspected the failing proxy helper.
- `sed -n '1440,1505p' protac_builder/route_impl.py` — inspected the builder’s `/api/e3ligase/pdb/...` wrapper.
- `sed -n '430,520p' RANDY/e3_data_routes.py` — verified RANDY’s listing and file routes.
- `python -m py_compile app.py protac_builder/e3_handoff.py protac_builder/route_impl.py protac_builder/api_routes.py` — passed.
- `python - <<'PY' ... mocked Flask test client and patched protac_builder.e3_handoff.requests.get ... PY` — passed exact-match, `_1` variant fallback, missing-file, and traversal validation.
- `python - <<'PY' from protac_builder.e3_handoff import normalize_e3_base_url ... PY` — confirmed host-root, `/backup/e3`, and duplicated `/backup/e3/backup/e3` inputs normalize correctly.

## Validation Results
- Route ownership confirmed: `/api/e3ligase/pdb/<ligase>/<path:filename>` is defined in `protac_builder/api_routes.py` and implemented in `protac_builder.route_impl.e3ligase_pdb_file()`.
- Failing log origin confirmed: `all upstream bases returned 404` came from `protac_builder/e3_handoff.py`.
- Upstream URL shape confirmed: the builder now targets normalized bases plus `GET /backup/e3/ligase-pdbs/<ligase>` and `GET /backup/e3/file/pdb/<ligase>/<filename>`.
- Base normalization validation passed:
  - `https://randy.rove-vernier.ts.net` -> `https://randy.rove-vernier.ts.net/backup/e3`
  - `https://randy.rove-vernier.ts.net/backup/e3` -> unchanged
  - `https://randy.rove-vernier.ts.net/backup/e3/backup/e3` -> deduplicated to one `/backup/e3`
  - `static/converted_sessions` -> ignored for E3 remote proxying
- Mock exact match passed: `GET /api/e3ligase/pdb/VHL/4B9K_TG0.pdb` returned `200` with `chemical/x-pdb`.
- Mock variant fallback passed: `GET /api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb` resolved through RANDY listing data to an available upstream file and returned `200`.
- Path traversal rejection passed: `GET /api/e3ligase/pdb/VHL/../secret.pdb` returned `400` with `{"ok": false, "error": "Invalid filename." ...}`.
- Missing file passed: `GET /api/e3ligase/pdb/VHL/DOES_NOT_EXIST.pdb` returned a clean `404` JSON response instead of a generic `500`.
- Existing molecule and session endpoints were not modified in this patch.

## Known Issues
- Live RANDY inventory for VHL was not queried from this workspace, so I could not prove whether production currently serves `4B9K_TG0.pdb`, `4B9K_TG0_1.pdb`, or another exact variant.
- The builder still carries stale-looking VHL filenames in `static/data/ligases.json`, but the proxy now resolves those safely without requiring a metadata migration.
- The route still falls back to historical hard-coded upstream hosts if no preferred env var is set; that behavior was intentionally preserved.

## Manual Verification
1. Open a builder session that uses a VHL recruiter.
2. Confirm `/api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb` no longer fails due to missing variant resolution.
3. Confirm the 3D viewer loads the E3 ligase PDB or shows a clean not-found message.
4. Confirm existing molecule modification and PROTAC logging still work.

## Suggested Next Prompt
Run one live production check against the deployed builder and RANDY for `/api/e3ligase/pdb/VHL/4B9K_TG0_1.pdb` so we can confirm which exact VHL filename RANDY currently serves in production.
