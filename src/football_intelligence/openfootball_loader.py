from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from football_intelligence.providers.openfootball import OpenFootballDataset, OpenFootballFixture


@dataclass(frozen=True)
class OpenFootballLoadResult:
    competition_code: str
    fixtures_seen: int
    matches_inserted: int
    matches_updated: int
    observations_inserted: int


def _one(cursor: Any) -> int:
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Expected database statement to return an identifier")
    return int(row[0])


def _season_id(cursor: Any, dataset: OpenFootballDataset) -> int:
    start_year = int(dataset.season[:4])
    cursor.execute(
        """INSERT INTO dim_season (label,start_date,end_date,status,data_as_of)
           VALUES (%s,%s,%s,'IN_PROGRESS',%s)
           ON CONFLICT (label) DO UPDATE SET
             start_date=COALESCE(dim_season.start_date,EXCLUDED.start_date),
             end_date=COALESCE(dim_season.end_date,EXCLUDED.end_date),
             data_as_of=GREATEST(dim_season.data_as_of,EXCLUDED.data_as_of)
           RETURNING season_id""",
        (dataset.season, f"{start_year}-07-01", f"{start_year + 1}-06-30", dataset.checked_at),
    )
    season_id = _one(cursor)
    cursor.execute(
        """INSERT INTO bridge_season_provider (season_id,provider,provider_season_id)
           VALUES (%s,'openfootball',%s) ON CONFLICT DO NOTHING""",
        (season_id, dataset.season),
    )
    return season_id


def _competition_id(cursor: Any, dataset: OpenFootballDataset) -> int:
    cursor.execute(
        """SELECT competition_id FROM bridge_competition_provider
           WHERE provider='openfootball' AND provider_competition_id=%s""",
        (dataset.competition_code,),
    )
    found = cursor.fetchone()
    if found:
        return int(found[0])
    cursor.execute(
        """INSERT INTO dim_competition (canonical_name,competition_type)
           VALUES (%s,'LEAGUE') RETURNING competition_id""",
        (dataset.name.removesuffix(f" {dataset.season.replace('-', '/') }"),),
    )
    competition_id = _one(cursor)
    cursor.execute(
        """INSERT INTO bridge_competition_provider
           (competition_id,provider,provider_competition_id,provider_name)
           VALUES (%s,'openfootball',%s,%s)""",
        (competition_id, dataset.competition_code, dataset.name),
    )
    return competition_id


def _team_id(cursor: Any, name: str) -> int:
    provider_id = name.casefold()
    cursor.execute(
        """SELECT team_id FROM bridge_team_provider
           WHERE provider='openfootball' AND provider_team_id=%s AND valid_to IS NULL""",
        (provider_id,),
    )
    found = cursor.fetchone()
    if found:
        return int(found[0])
    cursor.execute(
        "SELECT team_id FROM dim_team WHERE lower(canonical_name)=lower(%s) ORDER BY team_id",
        (name,),
    )
    candidates = cursor.fetchall()
    if len(candidates) == 1:
        team_id, confidence, method = int(candidates[0][0]), 0.95, "exact_name_cross_provider"
    else:
        cursor.execute(
            "INSERT INTO dim_team (canonical_name,team_type) VALUES (%s,'CLUB') RETURNING team_id",
            (name,),
        )
        team_id, confidence, method = _one(cursor), 1.0, "provider_seed"
    cursor.execute(
        """INSERT INTO bridge_team_provider
           (team_id,provider,provider_team_id,provider_name,confidence,match_method)
           VALUES (%s,'openfootball',%s,%s,%s,%s)""",
        (team_id, provider_id, name, confidence, method),
    )
    return team_id


def _payload(fixture: OpenFootballFixture) -> dict[str, Any]:
    # Retrieval time is observation metadata, not source content. Excluding it makes
    # an unchanged provider record idempotent across polling runs.
    return fixture.model_dump(mode="json", exclude={"data_as_of"})


def load_openfootball_dataset(
    cursor: Any, dataset: OpenFootballDataset, *, raw_object_uri: str
) -> OpenFootballLoadResult:
    season_id = _season_id(cursor, dataset)
    competition_id = _competition_id(cursor, dataset)
    inserted = updated = observations = 0
    for fixture in dataset.fixtures:
        home_team_id = _team_id(cursor, fixture.home_team)
        away_team_id = _team_id(cursor, fixture.away_team)
        cursor.execute(
            """SELECT match_id FROM bridge_match_provider
               WHERE provider='openfootball' AND provider_match_id=%s""",
            (fixture.provider_match_key,),
        )
        found = cursor.fetchone()
        score = fixture.score.full_time
        kickoff = datetime.combine(fixture.match_date, datetime.min.time(), tzinfo=UTC)
        if found:
            match_id = int(found[0])
            cursor.execute(
                """UPDATE dim_match SET competition_id=%s,season_id=%s,home_team_id=%s,
                   away_team_id=%s,kickoff_at=%s,status=%s,home_score=%s,away_score=%s,
                   data_as_of=%s WHERE match_id=%s""",
                (competition_id, season_id, home_team_id, away_team_id, kickoff, fixture.status,
                 score[0] if score else None, score[1] if score else None,
                 fixture.data_as_of, match_id),
            )
            updated += 1
        else:
            cursor.execute(
                """INSERT INTO dim_match (competition_id,season_id,home_team_id,away_team_id,
                   kickoff_at,status,home_score,away_score,data_as_of)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING match_id""",
                (competition_id, season_id, home_team_id, away_team_id, kickoff, fixture.status,
                 score[0] if score else None, score[1] if score else None, fixture.data_as_of),
            )
            match_id = _one(cursor)
            cursor.execute(
                """INSERT INTO bridge_match_provider
                   (match_id,provider,provider_match_id,source_label)
                   VALUES (%s,'openfootball',%s,%s)""",
                (match_id, fixture.provider_match_key, dataset.name),
            )
            inserted += 1
        payload = _payload(fixture)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        cursor.execute(
            """INSERT INTO source_observation (provider,entity_type,provider_entity_id,
               observed_at,source_url,source_license,raw_object_uri,content_hash,payload)
               VALUES ('openfootball','MATCH',%s,%s,%s,%s,%s,%s,%s::jsonb)
               ON CONFLICT DO NOTHING""",
            (fixture.provider_match_key, fixture.data_as_of, fixture.source_url, dataset.license,
             raw_object_uri, sha256(encoded).hexdigest(), encoded.decode()),
        )
        observations += max(cursor.rowcount, 0)
    return OpenFootballLoadResult(
        dataset.competition_code, len(dataset.fixtures), inserted, updated, observations
    )
