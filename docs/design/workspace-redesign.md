# Workspace design revision — 2026-09-30

The approved landing page supplies the workspace palette, local Manrope typography, open spacing and restrained rules. The desktop workspace uses a forest-green navigation rail; narrow screens use a horizontally scrollable navigation strip. The landing composition is preserved.

## Screens

- Players: open directory rows and a separate search/filter area, replacing profile cards.
- Player detail: plain typographic masthead, explicit historical season context, open statistics, restrained metric indicators and a single average-position marker.
- Recruitment: reference-player search first, expandable role creation, compact preference controls and ranked evidence rows.
- Shortlists: list/detail layout, visible selected state and preserved candidate workflow controls.
- Comparison: named player columns, readable per-90 values and percentiles without decorative bars.
- Market: consistent search, analysis and availability sections.
- Squad: clear planning-input requirements and links to available recruitment workflows.
- Coverage: open source statistics, readable tables and source notes.

## Validation

- TypeScript check passed.
- Docker production build passed and web service restarted at localhost:13000.
- Browser: player filtering, Toni Kroos profile, live similarity search, two-player comparison with eight metrics, existing shortlist selection, role disclosure/preset controls, text tone analysis and coverage filtering checked.
- No shortlist or role records created, archived or modified during this review.
- All seven workspace routes checked for narrow-screen document overflow; none found. Final directory also checked at 390 and 1440 CSS pixels. Temporary viewport override reset.
- Landing visual regression checked; browser error log empty at final check.
- Screenshots: workspace-redesign.png and workspace-mobile.png.

Licensed valuation and squad inputs remain unavailable. This revision changes presentation and preserves those existing feature limits.
