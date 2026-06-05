# Qodex.summary

## Task
Fix the `/builder` desktop layout regression caused by the mobile interface update.

## Original Goal
The user wants the regular PROTAC Builder page to look great on mobile, but the recent update broke the computer/desktop layout and caused ChemDoodle controls to render as long vertical columns. The goal is to restore desktop while keeping mobile polished.

## Assumptions
- Desktop behavior above `1024px` should remain as close as possible to the pre-mobile builder layout.
- The recent wrapper markup in `templates/builder.html` can remain if desktop layout-changing CSS is removed from large screens.
- ChemDoodle injects its own control DOM into the editor wrapper, so parent display rules must not force those controls into a narrow flex column.
- Mobile/tablet enhancements should only activate at `1024px` and below.
- Mobile canvas fitting is still useful, but the helper JS must be a no-op on desktop and must clear any inline canvas sizing when resizing back up.

## Files Inspected
- `/Users/jxs794/Documents/PROTAC_BUILDER/templates/builder.html`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-builder-mobile.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/protac-builder-mobile.js`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/COPYstyles.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/ChemDoodleWeb.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/COPYscripts.js`

## Files Changed
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-builder-mobile.css`
  Reduced the global surface area to safe builder-only rules and moved all layout-changing mobile/tablet styling into `@media (max-width: 1024px)` and narrower breakpoints.
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/protac-builder-mobile.js`
  Gated canvas fitting behind `matchMedia("(max-width: 1024px)")`, added desktop inline-style cleanup, and prevented mobile resize work from mutating desktop layout.
- `/Users/jxs794/Documents/PROTAC_BUILDER/Qodex.summary.md`
  Replaced the previous summary with this regression-focused record.

## Files Created
- None.

## Implementation Summary
The root cause was CSS leakage from `static/css/protac-builder-mobile.css`, not a broken ChemDoodle mount point. The new `.builder-canvas-frame` wrapper was globally set to `display: flex`, and ChemDoodle injects its toolbar controls into that wrapper before the canvas. On desktop, that forced the toolbar into a very narrow stacked column and stretched the editor container vertically, which produced the long toolbar strip and the oversized pastel panels.

The fix was to make the mobile stylesheet truly mobile-only. I removed desktop-affecting base rules such as builder shell width overrides, workflow grid layout, canvas wrapper flex layout, parameter group wrapping, and modal spacing from the global scope. Those rules now only apply at `1024px` and below. On mobile, the canvas wrapper uses block flow with horizontal overflow protection instead of flex, so ChemDoodle controls can stay wide and readable without collapsing into a tall column.

The JS helper was also tightened. It now only fits ChemDoodle canvases when the builder is actually at mobile/tablet widths, and it explicitly clears inline `width` and `height` when the viewport returns to desktop.

## Key Decisions
- Preserved `templates/builder.html` wrapper markup because the markup itself was not the primary regression source.
- Used `1024px` as the strict mobile/tablet boundary.
- Kept only minimal safe global rules outside media queries: CSS variables, hidden mobile step headings on desktop, text wrapping, and z-index helpers.
- Did not modify ChemDoodle library files because the regression was caused by parent layout rules, not the library.
- Kept the mobile helper JS, but made desktop behavior an explicit no-op.

## Commands Run
- `pwd`
  Confirmed the project root.
- `git status --short`
  Confirmed the worktree was clean before edits.
- `git diff -- templates/builder.html static/css/protac-builder-mobile.css static/js/protac-builder-mobile.js`
  Reviewed the recent mobile changes.
- `sed -n '1,260p' static/css/protac-builder-mobile.css`
- `sed -n '260,620p' static/css/protac-builder-mobile.css`
- `grep -n "@media\|canvas\|ChemDoodle\|toolbar\|editor\|container\|row\|selector\|height\|width\|position\|display\|grid\|flex\|overflow" static/css/protac-builder-mobile.css`
  Audited CSS scope and identified layout-changing base rules.
- `sed -n '1,260p' static/js/protac-builder-mobile.js`
- `grep -R "querySelector\|querySelectorAll\|getElementById\|canvas\|ChemDoodle\|style.width\|style.height\|resize\|MutationObserver\|setTimeout\|matchMedia" -n static/js/protac-builder-mobile.js static/js/COPYscripts.js templates/builder.html`
  Reviewed the helper JS and ChemDoodle-related DOM mutations.
- `grep -n "ligand-editor\|linker-editor\|ligase-editor\|protac-sketcher\|builder-editor\|workflow\|step\|ChemDoodle" templates/builder.html`
- `grep -R "ligand-editor\|linker-editor\|ligase-editor\|protac-sketcher\|selector-box\|canvas\|ChemDoodle\|editor" -n templates/builder.html static/css/COPYstyles.css static/css/ChemDoodleWeb.css`
  Compared builder markup and legacy desktop styling.
- `git diff c1dc4af^ c1dc4af -- templates/builder.html static/css/protac-builder-mobile.css static/js/protac-builder-mobile.js`
  Compared the mobile update against the previous builder state.
- `python app.py`
  Started the local Flask app on `http://127.0.0.1:5069`.
- Browser automation against `/builder`
  Captured before/after screenshots, inspected ChemDoodle wrapper DOM, measured toolbar geometry, and validated breakpoints at `1440px`, `1280px`, `1024px`, `768px`, `430px`, and `390px`.
- `python -m py_compile app.py`
  Passed.
- `python -m py_compile protac_builder/routes.py`
  Passed.
- `node --check static/js/protac-builder-mobile.js`
  Passed.
- `grep -R "id=\"ligand-editor\"\|id=\"linker-editor\"\|id=\"ligase-editor\"\|id=\"protac-sketcher\"\|id=\"curatedLinkersModal\"\|id=\"protacModal\"\|id=\"cheats-notes-overlay\"" -n templates`
  Confirmed required IDs remain present.
- `grep -R "protac-builder-mobile.css\|protac-builder-mobile.js" -n templates`
  Confirmed the mobile assets are loaded only by `templates/builder.html`.

## Validation Results
- Desktop screenshot and DOM validation at `1440px` and `1280px` showed the original three-column selector and editor layout restored.
- Desktop and tablet transition check at `1024px` confirmed this is now the exact switchover into the mobile/tablet workflow styling.
- Mobile checks at `768px`, `430px`, and `390px` confirmed stacked sections, fitted canvases, and no horizontal overflow.
- `document.documentElement.scrollWidth === window.innerWidth` at `1440px`, `1280px`, `1024px`, `768px`, `430px`, and `390px`.
- ChemDoodle toolbar geometry after the fix:
  Desktop `1440px` and `1280px`: toolbar about `353px` wide by `116px` high, no tall vertical strip.
  Tablet `768px`: toolbar about `624px` wide by `58px` high.
  Mobile `390px`: canvas resized down to `276px` wide and stayed contained.
- Cheats & Notes still opens on mobile.
- Curated linker modal still opens on mobile.
- Mobile nav drawer still opens and closes back to its off-canvas state.

## Known Issues
- The breakpoint is intentionally strict at `1024px`, so `1024px` now uses the tablet/mobile layout by design.
- I did not change the legacy inline CSS in `templates/builder.html` beyond inspection because the regression was solved without touching desktop styling there.
- I did not run a full end-to-end PROTAC generation flow; validation focused on layout, editor containment, and key builder UI interactions.

## Manual Verification
1. Run the app from `/Users/jxs794/Documents/PROTAC_BUILDER` and open `http://127.0.0.1:5069/builder`.
2. At `1440px` and `1280px`, confirm the hero, three selectors, and three ChemDoodle editors appear in the original desktop arrangement.
3. Confirm the ChemDoodle controls are no longer a page-height vertical column and the canvases remain inside their cards.
4. At `1024px`, confirm the mobile/tablet sections appear and the layout changes to the stacked workflow style.
5. At `768px`, `430px`, and `390px`, confirm there is no horizontal overflow and the selector/editor cards stack cleanly.
6. Open Cheats & Notes and the curated linker modal on mobile widths and confirm they layer above the content correctly.
7. Open and close the mobile nav drawer and confirm it sits above page content.

## Suggested Next Prompt
Run one more `/builder` QA pass that exercises a full real PROTAC generation flow at `1280px` and `390px`, then clean up any remaining builder-specific inline CSS that is now redundant with the mobile stylesheet.
