# Qodex.summary

## Task
Improve the `/builder` curated linker modal on mobile without changing desktop behavior.

## Original Goal
The user wants the mobile linker selection modal to show actual linkers clearly and allow scrolling/selection, because the filters currently dominate the screen and make it hard to reach the linker cards. Desktop should remain unchanged, and the fixed periodic table layering should be preserved.

## Assumptions
- Desktop builder and desktop curated-linker modal behavior should remain unchanged.
- Mobile-specific curated-linker modal fixes can be safely scoped to `body[data-page="builder"]` and `max-width: 1024px` / `768px`.
- The rendered linker entries use `.linker-item` cards inside `#linkers-list`.
- Existing filter and pagination logic in `static/js/COPYscripts.js` should remain the source of data loading and selection state.
- On phones, filters being collapsed by default is a better first-run experience than forcing users through the full filter form before they can see linkers.
- The periodic table/dialog layering fix must remain as-is, with builder-page jQuery UI dialogs staying above normal content but below the mobile nav drawer.

## Files Inspected
- `/Users/jxs794/Documents/PROTAC_BUILDER/templates/builder.html`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-builder-mobile.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/protac-builder-mobile.js`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-modal.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/COPYstyles.css`
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/COPYscripts.js`

## Files Changed
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/css/protac-builder-mobile.css`
  Added mobile/tablet-only curated-linker modal layout overrides so the modal body becomes the main scroll container, filters can collapse cleanly, linker cards display in a friendlier mobile grid/list, and the modal header/footer remain usable without trapping content.
- `/Users/jxs794/Documents/PROTAC_BUILDER/static/js/protac-builder-mobile.js`
  Added builder-only mobile curated-linker modal helpers for collapsing filters by default on phones, syncing toggle text, scrolling focus back to the linker list after filter/pagination actions, and preserving desktop behavior.
- `/Users/jxs794/Documents/PROTAC_BUILDER/Qodex.summary.md`
  Replaced the previous summary with this linker-modal-specific implementation record.

## Files Created
- None.

## Implementation Summary
The root issue was a nested-scroll layout on mobile. The curated-linker modal body in `templates/builder.html` and `static/css/protac-modal.css` still behaved like a constrained flex shell with `overflow: hidden`, while both `#filters-container` and `#linkers-list` tried to scroll independently. On phones, the filter block expanded to consume most of the modal, the linker list was squeezed into a much smaller area, and the footer permanently occupied the bottom of the viewport.

I fixed that in the builder mobile stylesheet by making the modal body the primary scroll container on mobile/tablet widths, allowing the filter area and linker list to flow naturally inside it instead of each trapping scroll separately. The filter block can now collapse cleanly, the linker list uses a mobile-friendly grid/list layout, thumbnails scale safely, metadata wraps, and the footer buttons remain reachable without hiding the actual cards.

I also added small builder-only mobile JS so the curated-linker modal behaves more like a picker than a form on phones. Filters now start collapsed on phone widths, the toggle button text stays in sync, `Apply Filters` collapses the filters and returns focus to the results, and pagination also scrolls back toward the linker list so users stay oriented around the cards.

## Key Decisions
- Left `templates/builder.html` unchanged and solved the mobile modal issue in builder-scoped CSS/JS.
- Kept desktop curated-linker modal behavior unchanged by only applying the major overflow/grid changes inside mobile/tablet breakpoints.
- Chose the modal body as the single primary mobile scroll container instead of trying to keep both the filter pane and the list as separate scroll regions.
- Collapsed filters by default on phones, but not on desktop, so mobile users see linkers immediately while still keeping filters accessible.
- Preserved the existing filter/pagination/linker-selection logic in `static/js/COPYscripts.js` and only added focus/scroll helpers around it.
- Kept the previously fixed periodic-table/jQuery UI dialog z-index rules intact and verified they still resolve correctly.

## Commands Run
- `pwd`
  Confirmed the project root.
- `git status --short`
  Confirmed the worktree was clean before edits.
- `git diff -- templates/builder.html static/css/protac-builder-mobile.css static/js/protac-builder-mobile.js`
  Reviewed the current builder mobile state before patching.
- `grep -n "curatedLinkersModal\|toggle-filters\|filters-container\|linkers-list\|pagination-controls\|select-linker\|prev-page\|next-page" templates/builder.html`
  Located the curated-linker modal markup and key IDs.
- `grep -R "curatedLinkersModal\|filters-container\|linkers-list\|pagination-controls\|toggle-filters\|svg-thumb\|modal-body\|modal-footer\|modal-header" -n templates/builder.html static/css static/js`
  Audited all curated-linker modal CSS/JS touchpoints.
- `sed -n '1,340p' static/css/protac-builder-mobile.css`
- `sed -n '340,760p' static/css/protac-builder-mobile.css`
  Reviewed the current builder mobile stylesheet before patching.
- `sed -n '1,340p' static/js/protac-builder-mobile.js`
  Reviewed current builder-only mobile JS before adding modal helpers.
- `grep -R "linkers-list\|toggle-filters\|filters-container\|apply-filters\|select-linker\|prev-page\|next-page\|curatedLinkersModal" -n static/js templates`
  Confirmed existing curated-linker data loading and selection behavior in `COPYscripts.js`.
- `python app.py`
  Confirmed port `5069` was already in use by the running local app instance.
- Browser automation against `/builder`
  Reproduced the desktop/mobile curated-linker modal states, measured overflow/scroll behavior, validated filter toggle and pagination behavior, and confirmed selection state after the fix.
- `python -m py_compile app.py`
  Passed.
- `python -m py_compile protac_builder/routes.py`
  Passed.
- `node --check static/js/protac-builder-mobile.js`
  Passed.
- `grep -R "id=\"curatedLinkersModal\"\|id=\"toggle-filters\"\|id=\"filters-container\"\|id=\"linkers-list\"\|id=\"select-linker\"" -n templates`
  Confirmed required IDs remain present.

## Validation Results
- Desktop validation:
  `1280px` curated-linker modal retained the original desktop behavior: modal body still `display: flex` with hidden inner overflow, filters remained expanded by default, the list kept its desktop auto-scroll behavior, and no builder desktop layout changed.
  `scrollWidth === innerWidth` at `1280px`.
- Mobile validation:
  At `390px`, the curated-linker modal body now computes as `overflow-y: auto`, the filters start collapsed, the linker list uses a single-column layout, and the document has no horizontal overflow.
  At `390px`, the filter toggle starts as `Show Filters ▼`, expands to `Hide Filters ▲` when opened, and collapses again after `Apply Filters`.
  At `390px`, after `Apply Filters`, the modal body scroll position moves back toward the linker list and the list remains the focus.
  At `390px`, after tapping `Next`, the modal keeps the linker list area in focus rather than leaving the user stranded at the filters.
  At `390px`, selecting a linker still applies `.selected` and enables `#select-linker`.
- Additional responsive checks:
  Tablet/mobile layout changes were scoped to the builder mobile stylesheet; desktop widths retained the earlier restored layout.
- Periodic table/dialog layering:
  The builder-page `.ui-dialog.ui-front` z-index still resolves to `12890`, so the ChemDoodle periodic-table/dialog layering fix remains in place.

## Known Issues
- I validated the mobile curated-linker flow with live linker results, but I did not exhaustively test every possible filter combination or no-results state.
- The modal header title remains compact on very small widths because the close button still needs room, though it is now materially more usable and the close control no longer stretches across the header.
- I did not refactor any of the legacy inline curated-linker modal CSS in `templates/builder.html`; the mobile fixes were layered safely on top via the builder mobile stylesheet.

## Manual Verification
1. Run the app from `/Users/jxs794/Documents/PROTAC_BUILDER` and open `http://127.0.0.1:5069/builder`.
2. At `1280px` or `1440px`, confirm the builder desktop layout still looks the same and the curated-linker modal still behaves like the current desktop version.
3. Open the ChemDoodle periodic-table/dialog and confirm it still appears above editor containers.
4. At `390px`, `430px`, and `768px`, open the curated-linker modal from the linker selector.
5. Confirm the modal opens beneath the fixed nav, the title and close button are visible, and the filters can be shown/hidden.
6. Confirm filters start collapsed on phone widths so the linker cards are immediately visible.
7. Tap `Show Filters`, then `Apply Filters`, and confirm the modal returns focus to the linker cards.
8. Scroll through the linker list, use `Previous` / `Next`, and confirm pagination remains reachable without a scroll trap.
9. Select a linker and confirm the selected state is obvious and `Select Linker` becomes enabled.

## Suggested Next Prompt
Clean up the legacy curated-linker modal CSS in `templates/builder.html` and consolidate duplicated modal styling into the builder-specific stylesheet now that the mobile behavior is stable.
