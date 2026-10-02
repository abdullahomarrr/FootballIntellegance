from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import date
from pathlib import Path

from football_intelligence.backfill import run_backfill
from football_intelligence.coverage_loader import load_statsbomb_coverage
from football_intelligence.database import load_events
from football_intelligence.display_names import populate_display_names
from football_intelligence.expected_threat import ExpectedThreatModel
from football_intelligence.final_audit import collect_final_evidence
from football_intelligence.identities import (
    players_from_statsbomb_lineups,
    players_from_wyscout,
    resolve_provider_players,
    seed_provider_players,
)
from football_intelligence.identity_candidate_audit import audit_wyscout_candidates
from football_intelligence.identity_overrides import (
    apply_identity_override,
    load_identity_overrides,
)
from football_intelligence.identity_triangulation import triangulate_wyscout_candidates
from football_intelligence.ingestion import ingest_statsbomb_match, write_report
from football_intelligence.openfootball_backfill import backfill_openfootball
from football_intelligence.providers.api_football import APIFootballAdapter
from football_intelligence.providers.openfootball import OpenFootballAdapter
from football_intelligence.providers.statsbomb_open import StatsBombOpenAdapter
from football_intelligence.providers.wyscout_open import WyscoutOpenAdapter
from football_intelligence.social_loader import ingest_bluesky_player
from football_intelligence.spatial import build_spatial_profile, load_canonical_jsonl
from football_intelligence.sportsdb_loader import ingest_sportsdb_day
from football_intelligence.statsbomb_backfill import (
    backfill_statsbomb_season,
    write_season_result,
)
from football_intelligence.statsbomb_player_match import load_statsbomb_player_matches
from football_intelligence.wyscout_backfill import backfill_wyscout_country
from football_intelligence.wyscout_ingestion import ingest_wyscout_match, read_json_member
from football_intelligence.wyscout_metadata import load_wyscout_match_metadata
from football_intelligence.wyscout_player_match import load_wyscout_player_matches


def discover_statsbomb(output: Path) -> None:
    rows = StatsBombOpenAdapter().discover_big_five()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([row.model_dump(mode="json") for row in rows], indent=2) + "\n",
        encoding="utf-8",
    )


def discover_wyscout(output: Path) -> None:
    catalogue = WyscoutOpenAdapter().discover_catalogue()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(catalogue.model_dump_json(indent=2) + "\n", encoding="utf-8")


def discover_api_football(league_ids: list[int], output: Path) -> None:
    adapter = APIFootballAdapter(os.environ.get("API_FOOTBALL_KEY", ""))
    rows = [row for league_id in league_ids for row in adapter.discover_league(league_id)]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([row.model_dump(mode="json") for row in rows], indent=2) + "\n",
        encoding="utf-8",
    )


def discover_openfootball(season: str, competition_codes: list[str], output: Path) -> None:
    adapter = OpenFootballAdapter()
    datasets = [adapter.fetch_competition(season, code) for code in competition_codes]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([item.model_dump(mode="json") for item in datasets], indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="football-intelligence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover = subparsers.add_parser("discover-statsbomb")
    discover.add_argument("--output", type=Path, required=True)
    wyscout = subparsers.add_parser("discover-wyscout")
    wyscout.add_argument("--output", type=Path, required=True)
    wyscout_download = subparsers.add_parser("download-wyscout-file")
    wyscout_download.add_argument("--name", required=True)
    wyscout_download.add_argument("--output", type=Path, required=True)
    api_football = subparsers.add_parser("discover-api-football")
    api_football.add_argument("--league-id", type=int, action="append", required=True)
    api_football.add_argument("--output", type=Path, required=True)
    openfootball = subparsers.add_parser("discover-openfootball")
    openfootball.add_argument("--season", required=True)
    openfootball.add_argument("--competition-code", action="append", required=True)
    openfootball.add_argument("--output", type=Path, required=True)
    openfootball_load = subparsers.add_parser("backfill-openfootball")
    openfootball_load.add_argument("--season", required=True)
    openfootball_load.add_argument("--competition-code", action="append", required=True)
    openfootball_load.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    openfootball_load.add_argument("--report", type=Path, required=True)
    sportsdb_load = subparsers.add_parser("ingest-thesportsdb-day")
    sportsdb_load.add_argument("--date", type=date.fromisoformat, required=True)
    sportsdb_load.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    sportsdb_load.add_argument("--report", type=Path, required=True)
    identity_audit = subparsers.add_parser("audit-wyscout-identity-candidates")
    identity_audit.add_argument("--players", type=Path, required=True)
    identity_audit.add_argument("--report", type=Path, required=True)
    identity_audit.add_argument("--apply", action="store_true")
    triangulate = subparsers.add_parser("triangulate-wyscout-identities")
    triangulate.add_argument("--limit", type=int, default=30)
    triangulate.add_argument("--interval", type=float, default=2.1)
    triangulate.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    triangulate.add_argument("--report", type=Path, required=True)
    bluesky_load = subparsers.add_parser("ingest-bluesky-player")
    bluesky_load.add_argument("--player-id", type=int, required=True)
    bluesky_load.add_argument("--query", required=True)
    bluesky_load.add_argument("--limit", type=int, default=100)
    bluesky_load.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    bluesky_load.add_argument("--report", type=Path, required=True)
    ingest = subparsers.add_parser("ingest-statsbomb-match")
    ingest.add_argument("--match-id", type=int, required=True)
    ingest.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    ingest.add_argument("--canonical-root", type=Path, default=Path("data/canonical/events"))
    ingest.add_argument("--report", type=Path, required=True)
    wyscout_ingest = subparsers.add_parser("ingest-wyscout-match")
    wyscout_ingest.add_argument("--match-id", type=int, required=True)
    wyscout_ingest.add_argument("--country", required=True)
    wyscout_ingest.add_argument("--events-archive", type=Path, required=True)
    wyscout_ingest.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    wyscout_ingest.add_argument(
        "--canonical-root", type=Path, default=Path("data/canonical/events")
    )
    wyscout_ingest.add_argument("--report", type=Path, required=True)
    season = subparsers.add_parser("ingest-statsbomb-season")
    season.add_argument("--competition-id", type=int, required=True)
    season.add_argument("--season-id", type=int, required=True)
    season.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    season.add_argument("--canonical-root", type=Path, default=Path("data/canonical/events"))
    season.add_argument("--report-root", type=Path, default=Path("data/reports/matches"))
    season.add_argument("--checkpoint", type=Path, required=True)
    database_season = subparsers.add_parser("backfill-statsbomb-season")
    database_season.add_argument("--competition-id", type=int, required=True)
    database_season.add_argument("--season-id", type=int, required=True)
    database_season.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    database_season.add_argument(
        "--canonical-root", type=Path, default=Path("data/canonical/events")
    )
    database_season.add_argument(
        "--report-root", type=Path, default=Path("data/reports/statsbomb-matches")
    )
    database_season.add_argument("--checkpoint", type=Path, required=True)
    database_season.add_argument("--report", type=Path, required=True)
    statsbomb_player_match = subparsers.add_parser("load-statsbomb-player-matches")
    statsbomb_player_match.add_argument("--competition-id", type=int, required=True)
    statsbomb_player_match.add_argument("--season-id", type=int, required=True)
    statsbomb_player_match.add_argument("--report", type=Path, required=True)
    spatial = subparsers.add_parser("build-spatial-profile")
    spatial.add_argument("--events", type=Path, required=True)
    spatial.add_argument("--player-id", required=True)
    spatial.add_argument("--output", type=Path, required=True)
    threat = subparsers.add_parser("build-xt-profile")
    threat.add_argument("--events", type=Path, required=True)
    threat.add_argument("--output", type=Path, required=True)
    database = subparsers.add_parser("load-events-postgres")
    database.add_argument("--events", type=Path, required=True)
    identities = subparsers.add_parser("seed-statsbomb-lineup-identities")
    identities.add_argument("--match-id", type=int, required=True)
    wyscout_identities = subparsers.add_parser("resolve-wyscout-identities")
    wyscout_identities.add_argument("--players", type=Path, required=True)
    wyscout_identities.add_argument("--events", type=Path, required=True)
    wyscout_metadata = subparsers.add_parser("load-wyscout-match-metadata")
    wyscout_metadata.add_argument("--match-id", type=int, required=True)
    wyscout_metadata.add_argument("--country", required=True)
    wyscout_metadata.add_argument("--matches-archive", type=Path, required=True)
    wyscout_metadata.add_argument("--teams", type=Path, required=True)
    wyscout_metadata.add_argument("--competitions", type=Path, required=True)
    identity_overrides = subparsers.add_parser("apply-identity-overrides")
    identity_overrides.add_argument("--input", type=Path, required=True)
    wyscout_backfill = subparsers.add_parser("backfill-wyscout-country")
    wyscout_backfill.add_argument("--country", required=True)
    wyscout_backfill.add_argument("--events-archive", type=Path, required=True)
    wyscout_backfill.add_argument("--matches-archive", type=Path, required=True)
    wyscout_backfill.add_argument("--players", type=Path, required=True)
    wyscout_backfill.add_argument("--teams", type=Path, required=True)
    wyscout_backfill.add_argument("--competitions", type=Path, required=True)
    wyscout_backfill.add_argument("--report", type=Path, required=True)
    wyscout_player_match = subparsers.add_parser("load-wyscout-player-matches")
    wyscout_player_match.add_argument("--country", required=True)
    wyscout_player_match.add_argument("--events-archive", type=Path, required=True)
    wyscout_player_match.add_argument("--matches-archive", type=Path, required=True)
    wyscout_player_match.add_argument("--players", type=Path, required=True)
    wyscout_player_match.add_argument("--report", type=Path, required=True)
    coverage = subparsers.add_parser("load-statsbomb-coverage-postgres")
    coverage.add_argument("--input", type=Path, required=True)
    final_audit = subparsers.add_parser("audit-final-evidence")
    final_audit.add_argument("--output", type=Path, required=True)
    display_names = subparsers.add_parser("populate-display-names")
    display_names.add_argument("--no-llm", action="store_true")
    subparsers.add_parser("build-person-groups")
    subparsers.add_parser("build-spatial-snapshot")
    reep_parser = subparsers.add_parser("load-reep-crosswalk")
    reep_parser.add_argument("--file", type=Path, default=Path("data/external/reep/people.csv"))
    market_snapshot = subparsers.add_parser("load-market-snapshot")
    market_snapshot.add_argument(
        "--directory", type=Path, default=Path("data/external/transfermarkt_snapshot")
    )
    market_snapshot.add_argument("--dry-run", action="store_true")
    subparsers.add_parser("load-fotmob-squads")
    subparsers.add_parser("sync-fotmob-profiles")
    warm_parser = subparsers.add_parser("warm-fotmob-profiles")
    warm_parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.command == "discover-statsbomb":
        discover_statsbomb(args.output)
    elif args.command == "discover-wyscout":
        discover_wyscout(args.output)
    elif args.command == "download-wyscout-file":
        wyscout_adapter = WyscoutOpenAdapter()
        catalogue = wyscout_adapter.discover_catalogue()
        file_matches = [
            file
            for article in catalogue.articles
            for file in article.files
            if file.name == args.name
        ]
        if len(file_matches) != 1:
            raise ValueError(
                f"Expected one Wyscout file named {args.name}, found {len(file_matches)}"
            )
        wyscout_adapter.download_verified(file_matches[0], args.output)
        print(json.dumps({"file": args.name, "path": str(args.output)}, sort_keys=True))
    elif args.command == "discover-api-football":
        discover_api_football(args.league_id, args.output)
    elif args.command == "discover-openfootball":
        discover_openfootball(args.season, args.competition_code, args.output)
    elif args.command == "backfill-openfootball":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            openfootball_result = backfill_openfootball(
                connection,
                season=args.season,
                competition_codes=args.competition_code,
                raw_root=args.raw_root,
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(openfootball_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(openfootball_result), sort_keys=True))
    elif args.command == "ingest-thesportsdb-day":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            sportsdb_result = ingest_sportsdb_day(
                connection, day=args.date, raw_root=args.raw_root
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(sportsdb_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(sportsdb_result), sort_keys=True))
    elif args.command == "audit-wyscout-identity-candidates":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            identity_audit_result = audit_wyscout_candidates(
                connection, args.players, apply=args.apply
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(identity_audit_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(identity_audit_result), sort_keys=True))
    elif args.command == "triangulate-wyscout-identities":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            triangulation_result = triangulate_wyscout_candidates(
                connection,
                raw_root=args.raw_root,
                limit=args.limit,
                minimum_interval_seconds=args.interval,
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(triangulation_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(triangulation_result), sort_keys=True))
    elif args.command == "ingest-bluesky-player":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            bluesky_result = ingest_bluesky_player(
                connection,
                player_id=args.player_id,
                query=args.query,
                limit=args.limit,
                raw_root=args.raw_root,
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(bluesky_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(bluesky_result), sort_keys=True))
    elif args.command == "ingest-statsbomb-match":
        statsbomb_report = ingest_statsbomb_match(
            args.match_id,
            raw_root=args.raw_root,
            canonical_root=args.canonical_root,
        )
        write_report(statsbomb_report, args.report)
    elif args.command == "ingest-wyscout-match":
        wyscout_report = ingest_wyscout_match(
            args.match_id,
            country=args.country,
            events_archive=args.events_archive,
            raw_root=args.raw_root,
            canonical_root=args.canonical_root,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(wyscout_report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    elif args.command == "ingest-statsbomb-season":
        statsbomb_adapter = StatsBombOpenAdapter()
        season_matches = statsbomb_adapter.fetch_matches(args.competition_id, args.season_id)
        match_ids = [int(match["match_id"]) for match in season_matches]

        def ingest_one(match_id: int) -> None:
            match_report = ingest_statsbomb_match(
                match_id,
                raw_root=args.raw_root,
                canonical_root=args.canonical_root,
                adapter=statsbomb_adapter,
            )
            write_report(match_report, args.report_root / f"statsbomb-match-{match_id}.json")

        backfill_result = run_backfill(
            match_ids,
            checkpoint_path=args.checkpoint,
            ingest_match=ingest_one,
        )
        print(json.dumps(asdict(backfill_result), sort_keys=True))
    elif args.command == "backfill-statsbomb-season":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            season_result = backfill_statsbomb_season(
                connection,
                competition_id=args.competition_id,
                season_id=args.season_id,
                raw_root=args.raw_root,
                canonical_root=args.canonical_root,
                report_root=args.report_root,
                checkpoint=args.checkpoint,
            )
        write_season_result(season_result, args.report)
        print(json.dumps(asdict(season_result), sort_keys=True))
    elif args.command == "load-statsbomb-player-matches":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            statsbomb_player_match_result = load_statsbomb_player_matches(
                connection,
                competition_id=args.competition_id,
                season_id=args.season_id,
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(statsbomb_player_match_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(statsbomb_player_match_result), sort_keys=True))
    elif args.command == "build-spatial-profile":
        profile = build_spatial_profile(load_canonical_jsonl(args.events), args.player_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(profile.model_dump_json(indent=2) + "\n", encoding="utf-8")
    elif args.command == "build-xt-profile":
        model = ExpectedThreatModel()
        totals = model.player_totals(load_canonical_jsonl(args.events))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"model_version": model.version, "player_totals": totals}, indent=2) + "\n",
            encoding="utf-8",
        )
    elif args.command == "load-events-postgres":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        events = load_canonical_jsonl(args.events)
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            result = load_events(cursor, events)
        print(json.dumps(asdict(result), sort_keys=True))
    elif args.command == "seed-statsbomb-lineup-identities":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        players = players_from_statsbomb_lineups(
            StatsBombOpenAdapter().fetch_lineups(args.match_id)
        )
        with psycopg.connect(database_url) as connection:
            linked = seed_provider_players(connection, players)
        print(json.dumps({"match_id": args.match_id, "players_linked": linked}, sort_keys=True))
    elif args.command == "resolve-wyscout-identities":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        event_player_ids = {
            event.provider_player_id
            for event in load_canonical_jsonl(args.events)
            if event.provider_player_id
        }
        payload = json.loads(args.players.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Wyscout players file must contain a list")
        wyscout_players = players_from_wyscout(payload, player_ids=event_player_ids)
        with psycopg.connect(database_url) as connection:
            identity_result = resolve_provider_players(connection, wyscout_players)
        print(json.dumps(asdict(identity_result), sort_keys=True))
    elif args.command == "load-wyscout-match-metadata":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        matches = read_json_member(args.matches_archive, f"matches_{args.country}.json")
        if not isinstance(matches, list):
            raise ValueError("Wyscout matches archive member must contain a list")
        match = next((item for item in matches if int(item["wyId"]) == args.match_id), None)
        if match is None:
            raise ValueError(f"No Wyscout match metadata found for {args.match_id}")
        teams_payload = json.loads(args.teams.read_text(encoding="utf-8"))
        competitions_payload = json.loads(args.competitions.read_text(encoding="utf-8"))
        if not isinstance(teams_payload, list) or not isinstance(competitions_payload, list):
            raise ValueError("Wyscout teams and competitions files must contain lists")
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            metadata_result = load_wyscout_match_metadata(
                cursor,
                match=match,
                teams=teams_payload,
                competitions=competitions_payload,
            )
        print(json.dumps(asdict(metadata_result), sort_keys=True))
    elif args.command == "apply-identity-overrides":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        overrides = load_identity_overrides(args.input)
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            applied = sum(apply_identity_override(cursor, item) for item in overrides)
        print(json.dumps({"requested": len(overrides), "applied": applied}, sort_keys=True))
    elif args.command == "backfill-wyscout-country":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            country_backfill_result = backfill_wyscout_country(
                connection,
                country=args.country,
                events_archive=args.events_archive,
                matches_archive=args.matches_archive,
                players_path=args.players,
                teams_path=args.teams,
                competitions_path=args.competitions,
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(country_backfill_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(country_backfill_result), sort_keys=True))
    elif args.command == "load-wyscout-player-matches":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            player_match_result = load_wyscout_player_matches(
                connection,
                country=args.country,
                events_archive=args.events_archive,
                matches_archive=args.matches_archive,
                players_path=args.players,
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(player_match_result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(player_match_result), sort_keys=True))
    elif args.command == "load-statsbomb-coverage-postgres":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            loaded = load_statsbomb_coverage(cursor, args.input)
        print(json.dumps({"observations_loaded": loaded}, sort_keys=True))
    elif args.command == "populate-display-names":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            display_result = populate_display_names(connection, use_llm=not args.no_llm)
        print(json.dumps(asdict(display_result), sort_keys=True))
    elif args.command == "load-market-snapshot":
        import psycopg

        from football_intelligence.market_snapshot import load_snapshot

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            snapshot_report = load_snapshot(connection, args.directory, write=not args.dry_run)
        print(json.dumps(snapshot_report, sort_keys=True, default=str))
    elif args.command == "load-reep-crosswalk":
        import psycopg

        from football_intelligence.reep import load_crosswalk

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            loaded_ids = load_crosswalk(connection, args.file)
        print(json.dumps({"crosswalk_rows": loaded_ids}, sort_keys=True))
    elif args.command == "load-fotmob-squads":
        import psycopg

        from football_intelligence import fotmob

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            squad_report = fotmob.load_squads(connection)
            matched = fotmob.link_players(connection)
            squad_report["linked"] = fotmob.persist_links(connection, matched)
        print(json.dumps(squad_report, sort_keys=True, default=str))
    elif args.command == "sync-fotmob-profiles":
        import psycopg

        from football_intelligence import fotmob

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            sync_report = fotmob.sync_profiles_to_database(connection)
        print(json.dumps(sync_report, sort_keys=True))
    elif args.command == "warm-fotmob-profiles":
        import psycopg

        from football_intelligence import fotmob

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            warm_report = fotmob.warm_profiles(connection, limit=args.limit)
        print(json.dumps(warm_report, sort_keys=True, default=str))
    elif args.command == "build-person-groups":
        import psycopg

        from football_intelligence.person_groups import rebuild_person_groups

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            linked = rebuild_person_groups(connection)
        print(json.dumps({"linked_identities": linked}, sort_keys=True))
    elif args.command == "build-spatial-snapshot":
        import psycopg

        from football_intelligence.spatial_snapshot import build_spatial_snapshot

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection:
            snapshot_report = build_spatial_snapshot(connection)
        print(json.dumps(snapshot_report, sort_keys=True))
    elif args.command == "audit-final-evidence":
        import psycopg

        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://football:football-local-only@localhost:5432/football_intelligence",
        )
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            evidence = collect_final_evidence(cursor)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
