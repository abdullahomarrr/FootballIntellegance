# Football Intelligence — landing redesign brief

## Goal

Create a distinctive, beautifully composed football recruitment landing page with the visual authorship, coherent identity, and attention to detail expected from a leading design studio. Visitors should understand the product, inspect genuine evidence, and remember its visual character. Quality must come from composition, typography, product truth, and interaction craft rather than decorative complexity.

Scope of this document: analysis and art direction. The production redesign has not been implemented. Findings are based on the supplied critique and current page, navigation, stylesheet, and project documentation; this is not a rendered-browser visual audit.

## Findings

The current page repeats oversized condensed headings, feature panels, calls to action, and green analytical illustrations. The four navigation tiles repeat the header's routing function before visitors see a real result. The standalone hero postpones the evidence. Alternating feature panels explain broad concepts without showing a specific investigation. Repeated CSS overrides make coherent refinement harder.

The supplied critique is directionally useful but partly stale: the current page explicitly labels the footprint and radar as method previews. The fictional player and 94% score described in the critique are absent. The remaining problem is weak demonstration, not those specific false claims.

The proposed neutral palette, restrained type, and real data would improve credibility. They do not by themselves establish a memorable identity. A conventional hero, product panel, comparison table, and methodology section can remain generic even with honest content. Fixed colour percentages and categorical bans on cards are not substitutes for composition.

Do not publish the pasted database totals without verification. Player identities, comparable player-seasons, event counts, and current recruitment coverage are different concepts. Historical evidence must be visibly dated. Project documentation explicitly separates historical event coverage from credential-gated or licensed capabilities.

## Chosen direction: the recruitment dossier

A contemporary scouting publication with the precision of an analytical workbench. The page follows one real investigation: a player, the available evidence, a qualified comparison, and the decision that evidence can support. Use the dossier as an information structure, not as a theatrical paper prop.

The distinctive visual device is an evidence margin: a narrow column of season, source, sample, and short analytical annotations aligned to the content they explain. Fine rules and consistent alignment connect this margin across the page. On mobile, those annotations follow their corresponding evidence in reading order.

The identity should remain recognizable through type proportions, the margin, comparison marks, and layout rhythm even when the logo and green colour are removed. Avoid fake stamps, torn paper, handwriting, pitch wallpaper, floating dashboards, and decorative charts.

## Composition

1. **Masthead and opening spread.** Compact wordmark; Product, Coverage, Methodology; one Open workspace action. Use an asymmetric desktop composition with a concise headline on roughly five columns and a genuine player dossier on seven. Align their baselines and let the dossier extend below the opening text. Suggested working headline: “A closer look at your next signing.” Supporting copy must immediately identify player search, qualified comparison, and recorded rationale. Use one dominant action, “Explore players,” with a quieter coverage link. The headline is provisional and should be typeset in context.
2. **The evidence.** Continue the same dossier instead of introducing a disconnected feature block. Identify the real player, historical team, competition, season, minutes, and provenance. Show one meaningful chart and a short interpretation supported by its data. Choose the chart only after checking available evidence. Paired bars or distributions can communicate differences more clearly than a six-axis radar. A pitch belongs here only when real spatial events answer the question.
3. **The alternatives.** Introduce a visually quieter, full-width comparison ledger with up to three genuine candidates. Show the comparison population, understandable metric differences, and missing evidence. Similarity scores need their actual scale and method; do not convert an arbitrary score into a probability or describe it as transfer suitability. The question must match the endpoint's capabilities. Stronger pressing cannot be promised without comparable pressing evidence.
4. **The decision.** A compact explanation of how a user retains a rationale and moves to a shortlist. Show an existing shareable example only if available. Otherwise demonstrate the real interaction without inventing analyst notes or private scouting activity. One purposeful interaction can reveal the associated sample or comparison explanation; essential content remains available without hover or animation.
5. **Coverage and close.** One restrained forest-green section with a readable coverage summary, historical dates, methodology entry point, and the final workspace action. Show limitations next to the relevant claims. Avoid repeating another motivational headline. Footer supplies attribution and necessary navigation.

This sequence creates a large opening, a detailed reading passage, a compact comparison, and a quiet close. Section height follows content rather than making each feature a full viewport.

## Visual system

- Palette starting points: warm paper #F4F2EB, ink #18251F, forest #173D30, muted text #59665E. Lime can mark a selection or one action, but should not fill repeated sections. Validate actual foreground/background pairs before shipping.
- Typography: trial a restrained editorial serif for the opening statement against the existing Archivo for readable interface content. Select the actual family after checking licensing, rendering, and performance. Retain Barlow Condensed only if a specific display treatment earns its place. Never use condensed display type for dense evidence. Tabular numerals for metrics; uppercase limited to short metadata.
- Working sizes: display 68–88 px desktop and 40–48 px mobile; section headings 28–40 px; body 16–18 px; metadata normally 12–13 px. Adjust optically rather than enforcing an arbitrary scale.
- Grid: twelve columns desktop, generous outer gutters, and a consistent evidence margin. Mobile uses one intentional reading column. Use asymmetry in composition while keeping controls and data predictable.
- Shape: predominantly open surfaces and fine rules. Small radii for interactive controls; containment only where it expresses an actual group. Avoid placing every section inside a card.
- Brand: refine wordmark spacing and FI monogram geometry as part of the system. A monogram change alone will not establish identity.
- Imagery: optional rights-cleared football photography only when it supports the featured story. Do not add anonymous stadium imagery to manufacture atmosphere. No generated player likenesses as evidence.
- Motion: brief state transitions, approximately 160–220 ms, with no scroll hijacking, parallax, looping charts, or delayed content reveal. Honour reduced motion.

## Evidence and implementation contract

Select the example only after validating profile completeness and comparison availability. Bind every displayed metric to player ID, season, metric definition, unit, source, sample, and observation/snapshot date. Reuse production data contracts and chart primitives; the landing composition can be purpose-built rather than inheriting an entire application screen.

A generated versioned snapshot is acceptable and may be preferable to a live dependency for the landing. Label it accurately; “Live example” is inappropriate for a snapshot. On API failure, retain a clearly dated verified snapshot or an honest unavailable state. Never synthesize replacement results. Do not expose private shortlists.

Separate landing navigation and styles from application chrome deliberately. Existing global nav, heading, and section selectors require regression checks across the workspace. Replace obsolete landing rules once dependencies are identified instead of adding another override layer.

## Delivery sequence

1. Verify the evidence, choose the featured investigation, and write a plain-text narrative with no unsupported claims.
2. Typeset the opening spread and comparison passage at desktop and mobile sizes. Evaluate the distinctive margin, type pairing, and reading order before expanding the page.
3. Implement the complete narrative with real data contracts, source links, semantic structure, and meaningful actions.
4. Refine optical alignment, line breaks, chart labeling, interaction states, and responsive transitions across the entire page.
5. Review rendered output at 390, 768, 1440, and 1920 px; also check 320 px reflow, keyboard use, 200% zoom, reduced motion, long names, unavailable evidence, and slow font loading. Verify no workspace regressions.

## Acceptance criteria

- A first-time visitor can identify the audience, purpose, evidence, and next action after a brief viewing. Test with people; do not declare this achieved from code alone.
- The opening contains a readable piece of genuine product evidence without requiring a desktop scroll.
- Every visible number is traceable, dated where needed, and labelled with its unit and sample. Missing data remains missing.
- The page has one coherent investigation and no interchangeable feature-card filler.
- The evidence margin and typographic composition form a consistent, recognizable identity across desktop and mobile.
- All actions work, focus is visible, content does not depend on hover, and text meets WCAG AA contrast requirements.
- No clipped names, unreadable charts, accidental horizontal page scrolling, misleading freshness claims, or unfinished loading/error states.
- Visual review confirms deliberate spacing and type throughout; a build passing does not establish design quality.

## Reference lessons

SkillCorner describes concrete tracking, physical-performance, and game-intelligence capabilities and supports them with customer evidence. Borrow that specificity, not its styling: https://www.skillcorner.com/sports/football

Hudl Statsbomb explains differentiated models such as On-Ball Value and their analytical purpose. Borrow the connection between evidence and a football question, not a branded chart style: https://www.hudl.com/en_gb/products/statsbomb

These are content-positioning references reviewed for this brief, not a claim of a comprehensive visual competitor audit. Originality cannot be guaranteed globally, and a claimed agency budget is not an objective quality measure. The acceptance criteria above make the ambition reviewable.

## Implementation — 2026-09-30

Implemented the editorial landing in app/page.tsx with isolated landing and navigation CSS modules. Replaced illustrative charts with a versioned API snapshot of Toni Kroos, Spanish first division 2017/18, and three real model results. The refresh script validates the featured identity, season and required metrics before overwriting evidence. Removed obsolete landing-only CSS. Workspace screens retain their existing navigation.

Validation: TypeScript and production build pass; Docker web rebuilt at http://localhost:13000. Browser verified desktop and mobile layouts without horizontal page overflow, methodology disclosure, and navigation to a successfully loaded Toni Kroos profile. The snapshot is historical and intentionally works without a live API; linked workspace pages require the API. Screenshot: design/landing-redesign-desktop.png. Full accessibility and cross-browser audits remain separate from these checks.

## Revision 2 — 2026-09-30

User feedback supersedes the dossier/card direction above. Removed the entire hero profile card, serif and italic display typography, comparison bars and beige paper treatment. Reviewed SkillCorner's What We Do and Global Data sections in the browser; adopted their open split-section layout and unboxed figures without copying their brand or claims.

The new direction uses a full-width licensed stadium photograph, a direct recruitment headline, locally hosted Manrope throughout the landing and masthead, white content sections, restrained mint accents, and a unified dark footer. Retained the useful historical passing-profile section. Comparison rows show genuine values and the actual passing-volume percentile differences from Kroos. Added a dated coverage snapshot, explicitly separating current fixtures from historical StatsBomb catalogue data.

Validation: TypeScript check and Docker production build passed. Browser reviewed at desktop, 768px, 390px and 320px; no horizontal document overflow or elements outside the viewport in those checks. Verified disclosure opening and comparison navigation. Full accessibility audit and user testing have not been performed. Sources and license notes are in design/asset-sources.md.
