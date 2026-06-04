# Qodex.summary

## Task
Fix PROTAC Builder warhead export so `PDB + ligand code` selections produce a real `Warhead.sdf` for ZIP generation.

## Original Goal
Preserve the existing 2D MOL-block workflow for drawing and SMILES generation, but when a user chooses a warhead by PDB ID plus ligand code, fetch the actual source-backed ligand artifact needed for `Warhead.sdf` in the PROSETTAC ZIP.

## Assumptions
- `savedMolecule` must remain usable for the 2D builder flow and should not become the only source of truth for ZIP export.
- For a manual warhead `PDB + ligand` selection, the best export artifact is the ligand extracted from that PDB if possible.
- If ligand extraction from the PDB block fails, an RCSB chemical component SDF fallback is acceptable as a narrow fallback for ZIP export.

## Files Inspected
- `static/js/COPYscripts.js` — traced `useWarheadCodes()`, `finalizeProtac()`, `finalizeManualProtac()`, and `createZipFile()`.
- `protac_builder/route_impl.py` — added the new backend route for warhead SDF retrieval/extraction.
- `protac_builder/api_routes.py` — registered the new public warhead SDF route.
- `protac_builder/chemistry.py` — reviewed existing RDKit utilities before choosing where to implement PDB ligand extraction.
- `/Users/jxs794/Downloads/protac-builder-logs-1780533153287.txt` — reviewed the live console/log symptoms showing ligase export SDF exists while ZIP still fails.

## Files Changed
- `static/js/COPYscripts.js` — added a dedicated export-only warhead SDF cache and wired the `PDB + ligand` flow to populate it.
- `protac_builder/route_impl.py` — added `/api/warhead/sdf/<pdb_id>/<ligand_code>` and backend ligand-extraction helpers.
- `protac_builder/api_routes.py` — registered the warhead SDF route.
- `Qodex.summary.md` — updated task summary.

## Files Created
- `Qodex.summary.md` — current task summary.

## Implementation Summary
The bug was straightforward once the export path was isolated:

- entering a warhead `PDB + ligand code` updated session state,
- fetching the warhead PDB happened later,
- but no code ever fetched or cached `Warhead.sdf`.

So ZIP generation still depended on `savedMolecule`, which only existed for:

- hunter/target imports, or
- the editable 2D sketcher flow.

That meant the app could successfully:

- build the PROTAC,
- generate SMILES,
- cache `Ligase.sdf`,

and still fail at ZIP time because `Warhead.sdf` had never been created for the manual `PDB + ligand` path.

The fix mirrors the ligase export pattern:

1. Added a new export-only frontend key:
   - `exportWarheadSdf`
2. Added backend route:
   - `/api/warhead/sdf/<pdb_id>/<ligand_code>`
3. Backend route behavior:
   - fetches the PDB from RCSB,
   - extracts the requested ligand’s HETATM/CONECT block,
   - converts that extracted ligand into SDF with RDKit,
   - falls back to `https://files.rcsb.org/ligands/download/<ligand>_ideal.sdf` if direct extraction fails.
4. Frontend `useWarheadCodes()` now:
   - stores `warheadPdb`, `warheadLigand`, and `ligandHead2`,
   - clears stale export state,
   - immediately fetches and caches the export-grade `Warhead.sdf`.
5. `finalizeProtac()` and `finalizeManualProtac()` now ensure the warhead export SDF is present before ZIP generation.
6. `createZipFile()` now prefers the dedicated export warhead SDF cache, but still falls back to `savedMolecule` for existing hunter/import flows.

## Key Decisions
- Kept the editable warhead MOL flow intact.
- Did not replace `savedMolecule` for existing hunter/import cases; instead, added a parallel export-only key.
- Implemented PDB-based ligand extraction server-side so the ZIP can use a source-backed artifact instead of sketcher geometry.
- Added an RCSB ideal-SDF fallback only when ligand extraction from the PDB is not possible.

## Commands Run
- `rg -n "warhead.*sdf|target_pdb|warhead_sdf|RCSB|extract.*ligand|fetch.*ligand|ligand code|SDF" protac_builder static/js/COPYscripts.js` — identified existing warhead import/export paths.
- `sed -n '2988,3135p' static/js/COPYscripts.js` — inspected finalize and ZIP-preparation logic.
- `sed -n '3400,3488p' static/js/COPYscripts.js` — inspected manual warhead code-entry flow.
- `python - <<'PY' ... requests.get('https://files.rcsb.org/ligands/download/A84_ideal.sdf') ... PY` — confirmed RCSB ideal ligand SDF download shape.
- `python -m py_compile app.py protac_builder/e3_handoff.py protac_builder/route_impl.py protac_builder/api_routes.py` — passed.
- `node --check static/js/COPYscripts.js` — passed.
- `python - <<'PY' ... client.get('/api/warhead/sdf/4B9K/TG0') ... PY` — passed with `200` and `X-Warhead-SDF-Source: pdb-extracted`.
- `python - <<'PY' ... client.get('/api/warhead/sdf/XXXX/ZZZ') ... PY` — returned clean `404`.
- `python - <<'PY' ... client.get('/api/warhead/sdf/../ZZZ') ... PY` — returned clean `400`.

## Validation Results
- Python syntax validation passed.
- Frontend syntax validation passed.
- Route validation passed for:
  - extracted ligand from real PDB: `GET /api/warhead/sdf/4B9K/TG0` -> `200`, source `pdb-extracted`
  - missing warhead combination -> clean `404`
  - invalid path -> clean `400`
- The frontend now has the required hook so a manual warhead `PDB + ligand` selection attempts to cache `Warhead.sdf` immediately rather than waiting until ZIP creation.

## Known Issues
- Not every `PDB + ligand` pair is guaranteed to yield a successful extraction from the public RCSB PDB file. Some will rely on the ideal-component fallback.
- Full live browser verification of the exact production warhead pair you entered still needs to be run after deploy.

## Manual Verification
1. Open PROTAC Builder.
2. Enter a warhead PDB ID and ligand code manually.
3. Confirm the UI reports that the warhead export SDF was fetched.
4. Generate the PROTAC ZIP.
5. Confirm `Warhead.sdf` and `Warhead.pdb` are both present.
6. Confirm 2D editing and SMILES generation still work as before.

## Suggested Next Prompt
After deploy, test the exact manual warhead `PDB + ligand` pair from your session and inspect whether the backend reports `X-Warhead-SDF-Source: pdb-extracted` or `rcsb-ideal`, then tighten the fallback behavior if you want only PDB-extracted ligands for export.
