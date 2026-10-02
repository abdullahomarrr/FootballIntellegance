# Risk register

| ID | Risk | Likelihood | Impact | Evidence / trigger | Mitigation | Owner gate |
|---|---|---:|---:|---|---|---|
| R1 | No live 2026/27 spatial event source | High | High | open datasets are historical/selected | make spatial tier optional; commercial adapter later | product |
| R2 | API-Football historical player depth differs by season | High | High | provider says detailed coverage varies | authenticated discovery and sample reconciliation before backfill | data |
| R3 | Market-value licensing unavailable/expensive | High | High | no approved source in audit | defer valuation target; never scrape Transfermarkt | legal/product |
| R4 | Transfer fees/contracts sparsely populated | High | Medium | endpoint presence does not imply field completeness | profile null rates by league/season; show unknown | data |
| R5 | Social API access/retention restrictions | High | Medium | Reddit requires approval/agreement for many uses | remove from MVP; aggregate/minimize only after approval | legal |
| R6 | News production cost | Medium | Medium | free NewsAPI is dev-only; paid starts high | local metadata prototype; procurement gate | product |
| R7 | Cross-provider identity false merges | High | High | common names, aliases, missing DOB | conservative thresholds, review queue, reversible overrides | data |
| R8 | Open event catalogue is partial within a season | Medium | High | catalogue row does not prove all fixtures | count/reconcile matches before claiming full coverage | data |
| R9 | Historical schemas/semantics change | High | Medium | provider fields vary over time | raw preservation, schema versions, contract tests | platform |
| R10 | Live corrections create non-idempotent facts | Medium | High | fixture/player stats can be revised | overlap windows, source timestamps, snapshots | platform |
| R11 | Quota/cost blowout during backfill | Medium | Medium | many player/fixture pages | dry-run request estimator, caching, checkpoints | platform |
| R12 | Missing metrics are treated as zero | Medium | High | multi-tier comparisons invite accidental imputation | null semantics, dbt tests, tiered models | analytics |
| R13 | Derived xG/xT presented as provider data | Medium | High | Wyscout has coordinates but no native xG | separate provider/derived namespaces and versions | analytics |
| R14 | Terms change after ingestion | Medium | High | provider/social terms are mutable | persist terms version/date; periodic legal review; deletion plan | legal |
| R15 | 2026/27 freshness is overstated | Medium | High | pipeline failure or delayed plan | expose last successful `data_as_of` and status | product |
| R16 | Premature infrastructure delays proof | Low | Medium | working local vertical slice now exists | defer Airflow/Kubernetes/MLflow; keep the implemented frontend thin | engineering |
