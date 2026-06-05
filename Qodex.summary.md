# Qodex.summary

## Task
Refine the `/builder` mobile interface without touching the restored desktop layout.

## Original Goal
The user wants mobile-only fixes for the regular PROTAC Builder page: remove the overlapping floating Step 3 Generate PROTAC section, eliminate huge empty editor container space, make Load from SMILES panels easy to use on mobile, and ensure the ChemDoodle periodic table appears in front of editor containers on mobile and desktop.

## Assumptions
- Desktop at `1280px` and wider must remain visually unchanged from the restored post-regression state.
- Mobile/tablet-specific layout fixes should stay scoped to `max-width: 1024px`.
- ChemDoodle injects its own toolbar and dialog DOM, so parent wrapper styling and jQuery UI dialog stacking are the safe places to intervene.
- The existing `toggleSmilesPanel(...)` handler should remain the source of truth for opening and closing SMILES panels.
- The periodic table and related ChemDoodle dialogs use jQuery UI `.ui-dialog.ui-front` wrappers, so raising that wrapper stack level is safer than altering ChemDoodle source.

## Files Inspected
- `/Users/jxs794/Documents/PROTAC_BUILDER/templates/builder.html`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-builder-mobile.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/protac-builder-mobile.js`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/COPYstyles.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/ChemDoodleWeb.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-nav.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/COPYscripts.js`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/ChemDoodleWeb-uis.js`

## Files Changed
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-builder-mobile.css`
  Removed the mobile sticky behavior from Step 3, reduced mobile editor-frame dead space, improved SMILES panel expansion, and added builder-scoped dialog z-index rules for ChemDoodle/jQuery UI popups.
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/protac-builder-mobile.js`
  Improved mobile-only SMILES panel behavior by tracking open editor cards and scrolling the active editor card into view more predictably on phones/tablets.
- `/Users/jxs794/Documents/PROTAC_BUILDER/Qodex.summary.md`
  Replaced the previous summary with this mobile-polish implementation record.

## Files Created
- None.

## Implementation Summary
The Step 3 overlap came from the mobile rule that kept `.builder-generate-section` sticky with its own `bottom` offset and `z-index`. That made the Generate PROTAC card float above earlier sections on narrow screens. I changed the mobile Step 3 section back to normal document flow so Step 1, Step 2, and Step 3 stack cleanly again.

The oversized empty editor space on mobile came from two things working together: the editor cards were still allowed to stretch, and the mobile canvas wrapper kept extra reserved height while the legacy canvas margins added more vertical padding. I changed the mobile `.builder-canvas-frame` to a compact column layout, removed its fixed minimum height, removed the extra canvas block margins inside that wrapper, and stopped the mobile editor cards from stretching to taller neighbors.

The SMILES panel itself was functional but cramped on mobile because the open state was still capped at `220px`, and the helper script only did a weak `scrollIntoView(..., block: "nearest")`. I expanded the open panel height to `420px`, kept the panel in the active card with more room for the textarea and button, added a mobile-only `has-open-smiles` state to the editor card, and changed the helper script to scroll the active editor card into view using the mobile nav height as the offset.

For the periodic table layering fix, I identified the relevant ChemDoodle popup path as the jQuery UI dialog wrapper around `#ligand-editor_atom_query_dialog` and its periodic-table canvas `#ligand-editor_atom_query_dialog_pt`. That wrapper was sitting at `z-index: 100`, which is far too low relative to the builder cards. I raised builder-page `.ui-dialog.ui-front` and `.ui-widget-overlay` to sit above normal page content while still staying below the mobile nav drawer stack.

## Key Decisions
- Left `templates/builder.html` unchanged because the mobile issues were resolved in the mobile stylesheet and helper JS.
- Removed sticky positioning from the mobile Generate PROTAC section instead of trying to preserve a floating CTA that was already overlapping content.
- Reduced mobile editor dead space by changing wrapper behavior and card stretching, not by shrinking or hiding ChemDoodle controls.
- Kept the existing SMILES open/close handler and improved the experience around it rather than rewriting builder logic in `COPYscripts.js`.
- Scoped the periodic table fix to builder-page jQuery UI dialog selectors so the change stays narrow and does not alter unrelated pages.
- Set the ChemDoodle dialog stack below `--protac-nav-drawer-z` so the mobile nav drawer still wins if both are present.

## Commands Run
- `pwd`
  Confirmed the project root.
- `git status --short`
  Confirmed the worktree was clean before edits.
- `git diff -- templates/builder.html static/css/protac-builder-mobile.css static/js/protac-builder-mobile.js`
  Reviewed the current builder mobile changes before patching.
- `sed -n '1,260p' static/css/protac-builder-mobile.css`
- `sed -n '260,620p' static/css/protac-builder-mobile.css`
- `grep -n "builder-generate-section\|sticky\|bottom:\|builder-canvas-frame\|min-height\|smiles-panel\|builder-editor-card\|builder-mobile-section\|overflow\|z-index" static/css/protac-builder-mobile.css templates/builder.html`
  Isolated the Step 3 sticky rule, editor frame sizing, SMILES panel constraints, and stack-related selectors.
- `sed -n '1,260p' static/js/protac-builder-mobile.js`
- `grep -R "smiles-toggle-btn\|scrollIntoView\|toggleSmilesPanel\|warhead-smiles-panel\|linker-smiles-panel\|ligase-smiles-panel" -n templates static/js static/css`
  Confirmed the existing panel open behavior and where mobile scroll logic lived.
- `grep -R "Periodic Table\|periodic\|ChemDoodle\|uis\|dialog\|ui-dialog\|ui-widget\|z-index" -n templates static/css static/js`
  Located ChemDoodle and jQuery UI dialog selectors and z-index baselines.
- `grep -n "builder-mobile-intro\|builder-mobile-section\|builder-generate-section\|builder-canvas-frame\|smiles-panel\|ligand-editor\|linker-editor\|ligase-editor" templates/builder.html`
  Reconfirmed the relevant builder markup and required IDs.
- `sed -n '430,490p' templates/builder.html`
  Reviewed the base SMILES panel CSS already present in the template.
- `sed -n '3840,3915p' static/js/COPYscripts.js`
  Confirmed `toggleSmilesPanel(...)` and preserved builder logic.
- `python app.py`
  Confirmed the local builder app was already running on port `5069`.
- Browser automation against `/builder`
  Reproduced the mobile overlap and SMILES issues, measured editor heights, inspected ChemDoodle dialog selectors, and validated breakpoints after the fix.
- `python -m py_compile app.py`
  Passed.
- `python -m py_compile protac_builder/routes.py`
  Passed.
- `node --check static/js/protac-builder-mobile.js`
  Passed.
- `grep -R "protac-builder-mobile.css\|protac-builder-mobile.js" -n templates`
  Confirmed the mobile assets are still loaded only by `templates/builder.html`.
- `grep -R "id=\"warhead-smiles-panel\"\|id=\"linker-smiles-panel\"\|id=\"ligase-smiles-panel\"\|id=\"ligand-editor\"\|id=\"linker-editor\"\|id=\"ligase-editor\"\|id=\"protac-sketcher\"" -n templates`
  Confirmed the required SMILES panel and ChemDoodle IDs remain present.

## Validation Results
- Desktop checks at `1440px` and `1280px` kept the original selector/editor three-column layout and normal ChemDoodle toolbar proportions.
- Desktop builder metrics after the fix:
  `1280px` kept `scrollWidth === innerWidth`, the editor wrapper stayed `display: block`, and the toolbar stayed about `353px` wide by `116px` tall.
- Tablet/mobile checks at `1024px`, `768px`, `430px`, and `390px` passed with `scrollWidth === innerWidth`.
- Step 3 validation:
  At `390px`, `.builder-generate-section` now computes as `position: static`, and its top is well below the Step 1 section instead of floating over it.
- Editor space validation:
  At `390px`, the mobile warhead editor frame dropped from about `432px` to about `399px`.
  At `768px`, the frame dropped to about `367px`.
- SMILES panel validation:
  At `390px`, opening Warhead SMILES kept the correct panel open, applied the `has-open-smiles` card state, and increased the panel max height to `420px`.
  The textarea and load button remained visible and tappable in the editor card screenshot.
- Periodic table/dialog validation:
  The ChemDoodle atom-query dialog wrapper resolves to `.ui-dialog.ui-front`.
  Its computed builder-page z-index now resolves to `12890`, above normal builder content and below the mobile nav drawer stack at `13000`.

## Known Issues
- I validated ChemDoodle dialog stacking through the actual dialog wrapper selector and computed z-index, but I did not complete a full user-driven periodic-table click path in browser automation because the hidden ChemDoodle radio/button controls are awkward to trigger headlessly.
- I did not modify any legacy inline CSS in `templates/builder.html`; there is still future cleanup value in moving more builder-specific styling out of the template.
- The tutorial flyover can still visually crowd the top of the viewport on very small screens, but it was not part of this requested scope.

## Manual Verification
1. Run the app from `/Users/jxs794/Documents/PROTAC_BUILDER` and open `http://127.0.0.1:5069/builder`.
2. Check desktop at `1440px` and `1280px` and confirm the selector row, editor row, buttons, and Generate PROTAC section still match the restored layout.
3. Open a ChemDoodle atom/periodic-table style popup on desktop and confirm it appears above the editor cards.
4. Check `1024px`, `768px`, `430px`, and `390px`.
5. Confirm Step 1, Step 2, and Step 3 now stack cleanly without Step 3 floating over other sections.
6. In each editor card, tap `Load from SMILES` and confirm the correct textarea and load button open visibly inside that card.
7. Confirm the page scrolls to a useful editor-card position on mobile after opening a SMILES panel.
8. Confirm the editor cards no longer have large blank vertical space below the ChemDoodle canvas and controls.
9. Open the mobile nav drawer and confirm it still layers above normal page content.

## Suggested Next Prompt
Run one more `/builder` mobile QA pass focused on the tutorial flyover and the generated PROTAC output area, then trim any remaining builder-specific inline CSS that overlaps with the mobile stylesheet.
