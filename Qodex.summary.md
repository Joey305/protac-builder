# Qodex.summary

## Task
Update PROTAC Builder examples page launch links.

## Original Goal
Make `/examples` functionally useful by replacing the generic BRD4 example with a HIV protease target PROTAC launch card and by making CRBN, VHL, and custom SMILES cards open PROTAC Builder with the correct query parameters.

## Assumptions
- The canonical internal builder route is `/builder`.
- The requested example IDs `DR7`, `CRBN_Y70`, and `VHL_3JS` should be treated as real builder inputs only after confirming they exist in project data and APIs.
- `/downstream-modeling-tools` is still a valid internal route because the router serves both `/downstream-modeling-tools` and `/downstream-modeling`.
- The builder already has query-parameter preload logic for `ligand`, `ligase`, and `smiles`, so the safest implementation is to improve visibility and failure handling rather than replace the preload flow.
- Because no browser automation runtime is installed in this environment, builder preload verification has to rely on source inspection, route rendering, and API-backed validation rather than a true DOM click-through test.

## Files Inspected
- `templates/pages/examples.html`
  Reviewed the current example cards and updated the key launch cards.
- `templates/pages/_macros.html`
  Confirmed `info_card` behavior for internal and external links.
- `templates/builder.html`
  Confirmed the builder uses `static/js/COPYscripts.js` and identified the relevant visible inputs and status elements.
- `static/js/COPYscripts.js`
  Inspected the builder’s URL query-parameter handling for `ligand`, `ligase`, and `smiles`.
- `protac_builder/routes.py`
  Confirmed `/examples`, `/builder`, `/downstream-modeling-tools`, and `/downstream-modeling` route behavior.
- `protac_builder/route_impl.py`
  Reviewed builder-side alias and context helpers and confirmed recruiter alias handling exists.
- `data/output_csvs/Ligand_Atoms_Smiles_part1.csv`
  Verified that ligand code `DR7` exists in the project’s ligand data.
- `static/smiles/Components-smiles-stereo-oe.smi`
  Verified that `DR7` exists in the component smiles source.
- `static/data/recruiter_pdb_map.json`
  Verified that recruiter IDs `CRBN_Y70` and `VHL_3JS` exist in the recruiter data.
- `Ligases/MODULE/e3-recruiter-mod/Ligases/CRBN/SDF/CRBN_Y70.sdf`
  Confirmed the CRBN recruiter asset exists.
- `Ligases/MODULE/e3-recruiter-mod/Ligases/VHL/SDF/VHL_3JS.sdf`
  Confirmed the VHL recruiter asset exists.

## Files Changed
- `templates/pages/examples.html`
  Replaced the generic BRD4 card with a HIV protease launch card and updated the CRBN, VHL, and custom SMILES cards to use functional builder query-parameter URLs and clearer workflow copy.
- `static/js/COPYscripts.js`
  Improved builder preload UX so URL-driven ligand and recruiter loads populate visible fields when possible and show clear success or failure alerts instead of failing only in the console.
- `Qodex.summary.md`
  Replaced the previous task summary with this examples-page summary.

## Files Created
- No new project files were created.

## Implementation Summary
The `/examples` page now works more like a launchpad than a gallery. The first four cards open real builder workflows: a HIV protease warhead example via `ligand=DR7`, a CRBN recruiter example via `ligase=CRBN_Y70`, a VHL recruiter example via `ligase=VHL_3JS`, and a starter custom-SMILES example via `smiles=CCCCC`.

On the builder side, the query-parameter support already existed, but it was mostly silent. I kept the existing preload flow and improved the UI behavior so successful URL-driven loads now announce themselves more clearly, populate relevant visible fields where possible, and show a clear builder warning if a ligand or recruiter code is not found.

I also fixed a follow-up issue in the custom-SMILES path where values like `CCCCC` could load successfully as raw SMILES and then still trigger a false “warhead code not found” warning. The newer handoff loader now respects the source of the incoming value, so `?smiles=...` is treated as SMILES instead of being re-guessed as a ligand code.

## Key Decisions
- The BRD4 card was replaced with `Build a HIV-Protease Target PROTAC` and now links to `/builder?ligand=DR7` as requested.
- `DR7` was verified from local ligand data:
  - `data/output_csvs/Ligand_Atoms_Smiles_part1.csv`
  - `static/smiles/Components-smiles-stereo-oe.smi`
- `CRBN_Y70` and `VHL_3JS` were verified from local recruiter data and assets:
  - `static/data/recruiter_pdb_map.json`
  - recruiter SDF files under `Ligases/MODULE/e3-recruiter-mod/Ligases/...`
- Builder query-parameter support for `ligand`, `ligase`, and `smiles` already existed in `static/js/COPYscripts.js`; I did not add a new preload system, I refined the existing one.
- I added explicit alert/status behavior for invalid ligand and recruiter preloads so missing values no longer fail only in the console.
- I then refined the newer handoff loader so source-tagged `smiles` inputs are not reclassified as ligand codes during the secondary boot pass.
- `/downstream-modeling-tools` was kept on the examples page because it is still a valid route, although `/downstream-modeling` also resolves to the same page.

## Commands Run
- `sed -n ...`, `rg -n ...`
  Inspected the examples page, macros, builder template, route definitions, query-parameter handling, and data files.
- `python -m py_compile app.py protac_builder/routes.py protac_builder/site_content.py`
  Passed; confirmed Python syntax after the edits.
- Flask test-client checks via `python - <<'PY' ...`
  Confirmed `/examples` renders with HTTP `200`, contains the new cards and URLs, and that the builder example URLs return HTTP `200`.
- Flask test-client API checks
  Confirmed:
  - `/api/ligand/data?ligand=DR7` returns `200`
  - `/api/ligase/render?ligase=CRBN_Y70` returns `200`
  - `/api/ligase/render?ligase=VHL_3JS` returns `200`
  - invalid ligand and ligase examples return `404`
- Static source checks via `python - <<'PY' ...`
  Confirmed the new alert messages and URL-preload hooks are present in `static/js/COPYscripts.js`.
- `node --check static/js/COPYscripts.js`
  Passed; confirmed the follow-up handoff-loader change did not introduce JavaScript syntax errors.
- Local live HTTP checks via `urllib.request.urlopen(...)`
  Confirmed `/examples`, `/builder?ligand=DR7`, `/builder?ligase=CRBN_Y70`, `/builder?ligase=VHL_3JS`, and `/builder?smiles=CCCCC` all return HTTP `200`.
- `git status --short`
  Checked the worktree state before finalizing.

## Validation Results
- Python syntax validation: passed.
- `/examples` render: passed with HTTP `200`.
- The first four functional example cards were confirmed in rendered HTML:
  - HIV protease target PROTAC
  - CRBN-based PROTAC
  - VHL-based PROTAC
  - custom warhead SMILES
- The required example URLs were confirmed in rendered HTML:
  - `/builder?ligand=DR7`
  - `/builder?ligase=CRBN_Y70`
  - `/builder?ligase=VHL_3JS`
  - `/builder?smiles=CCCCC`
- The builder pages for those URLs all returned HTTP `200`.
- Backend support for the requested ligand and recruiter IDs was confirmed through the live builder APIs.
- Invalid value checks returned `404` from the supporting APIs, and the front-end script now includes explicit alert/status messaging for those failures.
- The follow-up custom-SMILES fix was validated by source inspection and JS syntax check; the `smiles` handoff path now carries source metadata so it is not reinterpreted as a ligand code during the later boot loader.
- I could not run a true browser automation pass to watch the builder UI preload live because no browser automation runtime such as Playwright or Selenium is installed in this environment.

## Known Issues
- I could not fully complete a DOM-level click-and-watch validation of the builder preload UI because no browser automation runtime is installed in this environment.
- The worktree already contained unrelated modified files from earlier page work when I started this task. For this task, I only changed `templates/pages/examples.html`, `static/js/COPYscripts.js`, and `Qodex.summary.md`.
- The examples are functional workflow starters, not validated degraders, and the page should still be reviewed by the project or domain owner before public release.

## Manual Verification
1. Start the local app using the documented project command.
2. Open `/examples`.
3. Click `Open HIV protease example`.
4. Confirm `/builder?ligand=DR7` loads the expected ligand state.
5. Click `Open CRBN in Builder`.
6. Confirm `/builder?ligase=CRBN_Y70` loads the expected recruiter state.
7. Click `Open VHL in Builder`.
8. Confirm `/builder?ligase=VHL_3JS` loads the expected recruiter state.
9. Click `Open custom SMILES`.
10. Confirm `/builder?smiles=CCCCC` prepopulates the custom SMILES workflow.
11. Resize to mobile width and confirm the examples grid remains readable.

## Suggested Next Prompt
Turn the examples page into richer end-to-end case studies with screenshots, expected query parameters, and downstream modeling handoffs.
