# Final evidence questions

Assessment date: 2026-09-30. Counts below come from
`data/reports/final-evidence-after-full-ingest.json`, generated directly from PostgreSQL after
the corrected StatsBomb replay, four full-season loads and final dbt build.

1. **How many leagues are populated?** Five Big Five leagues are populated from Wyscout.
   StatsBomb adds catalogue coverage for the same league set. Evidence: Wyscout ingestion
   reports and `coverage-matrix.md`.
2. **How many seasons are populated?** 24 distinct canonical season IDs, including the
   current 2026-27 fixture season.
3. **What is the earliest season?** 1973/74.
4. **Is 2026/27 updating correctly?** Current fixture/result coverage is populated from
   OpenFootball: 2,364 fixtures across seven leagues, including 353 completed results and
   2,011 scheduled fixtures. Current player-performance coverage remains a **missing
   credential/approved-source limitation** and is not inferred from fixture availability.
5. **How many canonical players exist?** 8,389.
6. **What percentage of provider identities were successfully resolved?** 100% (7,549 of
   7,549 distinct provider/player pairs present in `fact_event` have an active canonical
   bridge). This denominator measures event-participant linkage, not speculative cross-provider
   deduplication; weak name-only candidates remain deliberately separate.
7. **How many player-season profiles exist?** 12,219, including 3,287 with at least 900 minutes.
8. **How many player-seasons have event-level spatial coverage?** 12,031 distinct canonical
   player/competition/season combinations have at least one event with both normalized
   coordinates.
9. **Which metrics exist at each coverage tier?** Eight validated player-match/profile
   metrics exist where event data is available: goals, assists, shots, shots on target,
   passes, key passes, tackles and interceptions. Broader/current, market and contextual
   tiers remain source-dependent; see `player-intelligence-methodology.md`.
10. **Does similarity use real player data?** Yes. It queries database-backed real
    player-season percentiles and returns per-feature differences.
11. **Has similarity been manually sanity-checked?** Yes at an engineering/football
    plausibility level across GK, DF, MD and FW. All 40 returned peers respected position and
    900-minute constraints, and the leading names were positionally plausible. Exact targets,
    peers and limitations are recorded in `similarity-sanity-validation.md`; this is not
    represented as an independent expert endorsement.
12. **How many historical valuation/transfer observations exist?** Zero validated licensed
    valuation observations. This is a **data-licensing limitation**.
13. **What dataset trained the valuation model?** None. The training/evaluation contract is
    implemented, but no model is represented as trained without legitimate as-of targets.
    This is a **data-licensing limitation**.
14. **Was temporal leakage checked?** Yes at the implementation and test boundary; the split
    is chronological and the audit is in `ml/leakage-audit.md`. A real fitted-model audit
    awaits licensed targets.
15. **What are the valuation model's actual test metrics?** None. Reporting fabricated
    metrics would be incorrect; this is a **data-licensing limitation**.
16. **Does the model return uncertainty intervals?** The interface supports intervals, but
    no production interval is returned because no legitimate model is fitted. This is a
    **data-licensing limitation**, not a zero-width or fake estimate.
17. **Does news use real sources?** No production news observations are loaded. This is a
    **missing credential/approved-source limitation**; the ingestion and provenance boundary
    exists and fails closed.
18. **Does social sentiment use real public data where access permits?** Yes, on a deliberately
    narrow basis. The database contains 100 deduplicated public Bluesky AppView posts and two
    daily aggregates linked conservatively to one player. The UI shows source, period, sample
    size and a context-only warning. It is not represented as a representative fan-opinion
    corpus or as evidence of player quality.
19. **Does recruitment search use real analytics rather than hardcoded results?** Yes. The
    recruitment UI calls the database-backed similarity endpoint and contains no candidate
    fixture list.
20. **Does squad optimization respect constraints?** Yes at the algorithm/test boundary.
    Exact constrained optimization is tested; the production screen refuses to invent costs
    or fit inputs.
21. **Are production application paths free of fake player data?** The completed source audit
    found no embedded fictional player observations in production paths; fixtures remain in
    tests only. Re-run the audit at the final commit.
22. **Are data limitations visible rather than hidden?** Yes. Unavailable current, market,
    news, social and squad inputs are exposed as gates and never coerced to zero.
23. **Can every major analytical output be traced back to its source?** Yes for populated
    Wyscout/StatsBomb analytics through provider identifiers, raw artifacts, checksums and
    pipeline runs. A live trace sampled StatsBomb match `15946` and provider player `5477`
    through 3,762 match events to Ousmane Dembélé's canonical player-match profile.
24. **Do all critical tests pass?** The current repository run passes 176 Python tests at
    82.67% coverage, Ruff, strict mypy and the ten-route Next.js production build. This
    includes explicit timeout/retry, rate-limit, malformed-payload, missing-field, database
    failure and unknown-identity scenarios. The last full warehouse baseline passed 20 dbt
    nodes/tests and the later advanced-intelligence selection passed six nodes/tests; newly
    added family, range, population and uniqueness tests parse successfully but await the next
    PostgreSQL run. Earlier primary routes passed narrow-viewport overflow checks. Live
    validation also created and
    edited a role, demonstrated that role fit changed the real recommendation ranking while
    balanced similarity remained separately visible, created and opened
    a role-linked shortlist, added Neymar from Kylian Mbappé's real similarity results with an
    evidence rationale, changed the workflow stage, and compared both players side by side.

## Final local boundary

The captured healthy local baseline measured the filterable player browser at 586 ms for the
default qualified sample and 37 ms for a fully filtered query. Docker Desktop currently cannot
recreate its Linux engine because its internal inference socket is inaccessible, so PostgreSQL,
API, web, new dbt tests and the newest browser changes require revalidation after that host-level
failure is cleared. A fresh identity review found 27 source-backed Wyscout candidates with
consistent names but insufficient corroboration; all remain pending rather than being merged by
name alone.
Credential and licensing limits remain exactly those stated above; they are not runtime failures.
