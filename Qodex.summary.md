# Qodex.summary

## Task
Fix PROTAC Builder ligase export so ZIP generation uses real source-backed ligase SDF/PDB artifacts instead of sketcher-derived MOL blocks.

## Original Goal
Keep the 2D MOL-block workflow for drawing and SMILES generation, but fetch and cache ligase SDF/PDB files from the recruiter/RANDY-backed sources so `Ligase.sdf` and `Ligase.pdb` in the ZIP preserve the 3D context expected by PROSETTAC.

## Assumptions
- `savedLigase` must remain a MOL block because the PROTAC-building flow still relies on it for 2D editing and SMILES generation.
- Ligase export artifacts should be sourced from recruiter/session payloads or from the ligase PDB-backed data source, not synthesized from the current sketcher geometry.
- Local recruiter data under `Ligases/MODULE/e3-recruiter-mod/Ligases/<ligase>/...` is a valid narrow fallback before remote RANDY SDF fetches.

## Files Inspected
- `static/js/COPYscripts.js` — traced ZIP assembly, ligase selection, recruiter selection, and session-storage usage.
- `protac_builder/route_impl.py` — inspected recruiter payloads and added a ligase SDF API route.
- `protac_builder/e3_handoff.py` — inspected E3 proxy helpers and extended them for remote SDF fetches.
- `protac_builder/api_routes.py` — registered the new ligase SDF API route.
- `static/data/recruiter_pdb_map.json` — confirmed `LR00550 -> VHL / 9GIO_A84.pdb`.
- `/Users/jxs794/Downloads/protac-builder-logs-1780532184890.txt` — confirmed live `/api/e3ligase/pdb/VHL/9GIO_A84.pdb` succeeds and the remaining failure is ZIP state, not PDB handoff.

## Files Changed
- `static/js/COPYscripts.js` — separated export-only ligase SDF state from editable `savedLigase`, fetched ligase SDFs from source-backed routes, and added safer ZIP diagnostics.
- `protac_builder/e3_handoff.py` — added remote ligase SDF fetching that reuses resolved PDB matches.
- `protac_builder/route_impl.py` — added `/api/e3ligase/sdf/<ligase>/<filename>` with local recruiter-file fallback and clean `400`/`404` handling.
- `protac_builder/api_routes.py` — registered `/api/e3ligase/sdf/<ligase>/<filename>`.
- `Qodex.summary.md` — updated summary for this export-artifact fix.

## Files Created
- `Qodex.summary.md` — current task summary.

## Implementation Summary
The real problem was that ligase export and ligase editing were sharing the same session key. The frontend had been using `savedLigase` both as:

- the editable 2D MOL block used for PROTAC generation, and
- the ZIP source for `Ligase.sdf`.

Those are not the same artifact. The 2D MOL block is useful for editing, but it does not preserve the recruiter/PDB-backed 3D context needed downstream.

The fix separates those concerns:

1. `savedLigase` now stays a MOL block for the editor/build flow.
2. A new export-only cache key stores the real ligase SDF text.
3. Recruiter/session loaders still cache `sdf_text` when they already have it.
4. When a ligase PDB is chosen directly or via recruiter selection, the frontend now requests `/api/e3ligase/sdf/<ligase>/<pdb_file>` and stores that response for ZIP export.
5. The backend SDF route first tries local recruiter data:
   - `SDF_4Download/<pdb_stem>.sdf`
   - `SDF/<ligase>_<ligand>.sdf`
6. If local files are absent, the backend reuses the E3 handoff resolution logic to find the real remote PDB match and then requests the paired RANDY SDF.

This means `Ligase.pdb` and `Ligase.sdf` can now come from the same source-backed ligase selection without disturbing the 2D builder state.

## Key Decisions
- Kept `savedLigase` as a MOL block instead of overloading it with SDF text.
- Added a dedicated ligase SDF route instead of trying to infer export artifacts from the sketcher.
- Preferred exact source-backed SDF files over generating an SDF from the current ligase editor state.
- Added explicit missing-input diagnostics in `createZipFile()` so future export failures show which artifact is absent.

## Commands Run
- `sed -n '2380,2515p' static/js/COPYscripts.js` — inspected ZIP generation and ligase export state.
- `sed -n '2580,3325p' static/js/COPYscripts.js` — inspected recruiter/PDB selection and finalize flows.
- `sed -n '500,620p' protac_builder/route_impl.py` — inspected recruiter and converted-session SDF payloads.
- `sed -n '1,320p' protac_builder/e3_handoff.py` — inspected E3 resolution helpers before extending them for SDF.
- `python -m py_compile app.py protac_builder/e3_handoff.py protac_builder/route_impl.py protac_builder/api_routes.py` — passed.
- `node --check static/js/COPYscripts.js` — passed.
- `python - <<'PY' ... client.get('/api/e3ligase/sdf/VHL/9GIO_A84.pdb') ... PY` — returned `200` with `X-E3-Ligase-SDF: 9GIO_A84.sdf`.
- `python - <<'PY' ... client.get('/api/e3ligase/sdf/VHL/4B9K_TG0_1.pdb') ... PY` — returned `200` with `X-E3-Ligase-SDF: VHL_TG0.sdf`.
- `python - <<'PY' ... client.get('/api/e3ligase/sdf/VHL/DOES_NOT_EXIST.pdb') ... PY` — returned clean `404`.
- `python - <<'PY' ... client.get('/api/e3ligase/sdf/VHL/../secret.pdb') ... PY` — returned clean `400`.

## Validation Results
- Python syntax validation passed.
- Frontend syntax validation passed.
- Route validation passed for:
  - exact ligase export SDF: `VHL / 9GIO_A84.pdb`
  - stale variant ligase export SDF: `VHL / 4B9K_TG0_1.pdb`
  - missing ligase file: clean `404`
  - path traversal rejection: clean `400`
- Live log evidence confirmed `/api/e3ligase/pdb/VHL/9GIO_A84.pdb` already succeeds in production, so this task addressed the remaining ZIP/export side of the workflow.

## Known Issues
- `Warhead.sdf` can still be absent if the user has only a 2D warhead MOL block and has not imported a source-backed warhead SDF. This patch intentionally focused on ligase artifacts.
- Live browser validation of the full ZIP flow after deployment still needs to be run in production.

## Manual Verification
1. Open a builder session and generate a PROTAC as usual.
2. Select a ligase PDB or recruiter such as `LR00550` (`VHL / 9GIO_A84.pdb`).
3. Confirm `/api/e3ligase/pdb/VHL/9GIO_A84.pdb` still loads.
4. Confirm `/api/e3ligase/sdf/VHL/9GIO_A84.pdb` returns source-backed SDF text.
5. Generate the ZIP and confirm it includes `Ligase.pdb` and `Ligase.sdf`.
6. Confirm 2D editing and SMILES generation still work.

## Suggested Next Prompt
Test the deployed ZIP flow in the browser and trace whether `Warhead.sdf` should also move to a dedicated source-backed export key instead of reusing `savedMolecule`.
