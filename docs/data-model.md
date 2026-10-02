# Canonical data model

The schema is based only on fields observed in candidate APIs/open datasets. Provider-specific payloads remain immutable raw objects; canonical columns are nullable and never use zero to mean “unavailable.”

## Identity and coverage

### `provider_coverage_observation`

Grain: one provider × plan × competition × season × capability × discovery run.

Key fields: `provider`, `plan`, `provider_competition_id`, `provider_season_id`, `competition_name`, `season_label`, `capability`, `status` (`DIRECT|DERIVABLE|UNAVAILABLE|PAID|UNKNOWN`), `checked_at`, `provider_updated_at`, `request_uri_redacted`, `raw_object_uri`, `checksum`, `terms_version`, `notes`.

### Dimensions and provider bridges

- `dim_player(player_id, canonical_name, normalized_name, birth_date, nationality_codes, preferred_foot, height_cm, created_at, updated_at)`
- `dim_team(team_id, canonical_name, country_code, team_type, created_at, updated_at)`
- `dim_competition(competition_id, name, country_code, competition_type)`
- `dim_season(season_id, label, start_date, end_date, status, data_as_of)`
- `bridge_player_provider(player_id, provider, provider_player_id, confidence, match_method, verified, evidence_json, valid_from, valid_to)`
- equivalent bridges for team, competition, match and season
- `player_alias(player_id, alias, normalized_alias, language, source, verified)`
- `entity_resolution_candidate(entity_type, provider, provider_id, candidate_id, score, signals_json, status, reviewer, decided_at)`

Do not force uncertain mappings. A provider record can remain unresolved and be reprocessed.

## Raw manifest

`raw_object_manifest(raw_object_id, provider, endpoint, request_parameters_json, ingestion_started_at, source_updated_at, pipeline_run_id, object_uri, byte_size, checksum_sha256, content_type, source_schema_version, http_status, terms_version)`

Raw bodies live in object storage partitioned by provider/endpoint/competition/season/ingestion date. Secrets and authorization headers are never stored.

## Football facts

- `fact_match`: one canonical match; scheduled/kickoff timestamps, teams, scores, status, venue, provider freshness.
- `fact_player_match`: one player × match × team; nullable started/minutes/position and provider-observed statistics.
- `fact_player_team_competition_season`: one player × team × competition × season; provider season totals and reconciliation status.
- `fact_event`: one provider event; canonical and provider IDs, period/time, player/team/match, event/sub-event/outcome, raw and normalized start/end coordinates, pressure/possession/body part, provider xG, derived fields, qualifier JSON, schema version.
- `fact_transfer`: one completed/reported transaction event with status and as-of timestamps; fee currency/amount are nullable and provenance is mandatory.
- `fact_injury`: an as-of-dated availability interval, source wording, normalized category and uncertainty.
- `fact_market_value`: one player × valuation date × source; amount/currency, valuation type and terms provenance.
- `fact_news`: article metadata, permitted snippet, canonical URL, publication time, source, language, story-cluster ID and entity-link confidence.
- `fact_social_aggregate`: day × player × platform/topic; counts and aggregate sentiment only by default.

## Event normalization

Canonical pitch is **105 × 68 metres**, left-to-right attacking direction. Preserve provider coordinates in `raw_x/raw_y/raw_end_x/raw_end_y` and its coordinate-system code. Normalized values remain null when orientation or location is unknown.

Wyscout’s percentage-like coordinates map as `x_m = raw_x * 1.05`, `y_m = raw_y * 0.68`, followed by an explicitly recorded orientation transform. StatsBomb uses its own 120 × 80 convention; map to metres but retain the original. Conversion fixtures must cover boundaries, missing endpoints, period changes and provider orientation rules.

## Analytical marts

- `mart_player_season_profile`: player × team × competition × season (do not merge mid-season teams by default)
- `mart_player_competition_season`: optional explicitly aggregated view
- `mart_player_season_snapshot`: profile × snapshot date for live-season reproducibility
- `mart_player_metric_percentile`: profile × metric × comparison population × feature version
- `mart_player_spatial_profile`: profile × spatial feature version
- `mart_player_similarity_feature`: profile × model tier/version × feature
- `mart_player_career_profile`: player-level trajectory assembled from season profiles

Every mart carries `data_as_of`, `coverage_level`, `source_run_ids`, `feature_version` and applicable `model_version`.

## Coverage-aware invariants

1. Missing is null, not zero.
2. A metric has both a value and provenance/availability state.
3. Season status is `IN_PROGRESS`, `FINAL`, or `PARTIAL` independently of coverage tier.
4. Similarity models are tiered (`BASIC`, `ADVANCED`, `SPATIAL`) and cannot silently impute an absent feature group.
5. Raw provider IDs never become canonical primary keys.
6. All mutable live outputs are reproducible from an as-of snapshot.

## Entity-resolution design

Pipeline:

1. Normalize Unicode, punctuation, whitespace, common particles and known aliases while retaining original text.
2. Generate candidates by exact birth date plus compatible name; then name/nationality/team/season blocks.
3. Score signals: exact DOB is strong; normalized/fuzzy name, nationality, club overlap, position and height are supporting evidence.
4. Auto-link only above a calibrated high threshold with no close runner-up.
5. Send ambiguous cases to `entity_resolution_candidate`; apply version-controlled manual overrides.
6. Keep a complete decision audit and allow a bad merge to be reversed.

Examples to test:

- diacritics: `João Cancelo` vs `Joao Cancelo`;
- aliases: `Heung-min Son` vs `Son Heung-Min`;
- collision: multiple players named `João Pedro`—name alone must never merge them;
- transfers: club mismatch is expected across adjacent dates and should not override exact DOB evidence;
- missing DOB: require multiple corroborating signals or manual verification.
