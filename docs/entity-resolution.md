# Entity resolution

## Canonical identity contract

Provider identifiers never become canonical keys. Players, teams, competitions, seasons,
and matches live in canonical dimensions and retain provider mappings in bridge tables.
Current mappings are temporal (`valid_from`/`valid_to`) where the schema permits it.

## Players

Wyscout supplies name, birth date, nationality, position, height, and preferred foot.
StatsBomb Open lineups supply name and nationality but not birth date. Resolution therefore
uses normalized names plus available corroborating attributes and automatically links only
when the high-confidence rules in `entity_resolution.py` pass. A name-only match is never
silently merged. Ambiguous cross-provider candidates are written for review; otherwise a
provider-specific canonical player is seeded. Version-controlled overrides are audited and
idempotent.

Events are linked only through the current provider bridge. This preserves provenance and
allows a mistaken identity to be reversed without changing the raw record.

## Teams and competitions

Wyscout entities are provider-seeded. StatsBomb teams reuse an existing canonical team only
when exactly one case-insensitive exact canonical name exists; otherwise a new entity is
created. The bridge records `exact_name_cross_provider` with 0.95 confidence or
`provider_seed` with 1.0 confidence. Competition aliases explicitly map the five provider
league names to the canonical Big Five dimensions. No fuzzy club-name merge is performed.

## Seasons and matches

Season labels normalize to `YYYY/YY`; this prevents `2017/2018` and `2017/18` from becoming
different canonical seasons. Matches are identified by provider bridge, not score or date,
and may coexist across providers until a separately validated cross-provider match linker
is implemented. Replays reuse the provider bridge and event upsert keys.

## Validation and limitations

Tests cover diacritics, aliases, collisions, missing dates of birth, exact-team reuse,
provider seeding, season normalization, override audit, and idempotency. StatsBomb lineup
participants in the loaded seasons resolve to their StatsBomb canonical bridge with zero
unresolved player-match rows. This does not prove that every StatsBomb player is merged with
the same Wyscout person: absent date-of-birth evidence intentionally prevents unsafe merges.

## Final database report

Captured 2026-09-29 after the final replay and dbt build:

- 8,389 active provider player identities: 5,821 StatsBomb Open and 2,568 Wyscout Open;
- 8,389 canonical player rows referenced by those active bridges;
- 7,549 distinct provider/player identities appearing in events, all 7,549 linked (100%);
- 1,872 conservative cross-provider review candidates remain `PENDING`;
- zero manual overrides have been applied; and
- all active player bridges currently retain `provider_seed` as their match method.

The absence of automatic cross-provider merges is intentional evidence discipline, not a
claim that similarly named players are different people. StatsBomb Open omits date of birth,
while this Wyscout release has incomplete nationality normalization. Merging the 1,872
name-led candidates without stronger club/DOB evidence would violate the rule against
name-only identity merges. They remain inspectable and can be resolved through the audited,
idempotent override path when corroborating evidence is supplied.

