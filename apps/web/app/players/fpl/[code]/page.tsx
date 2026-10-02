"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { API, EmptyState, Envelope, formatNumber, ordinal } from "../../../components";
import { PageLoader } from "../../../page-loader";

type Ranking = { label: string; value: number; percentile: number; cohort_size: number };
type SeasonRow = {
  season: string;
  minutes: number;
  goals: number;
  assists: number;
  expected_goals: number | null;
  expected_assists: number | null;
  clean_sheets: number;
  points: number;
};
type WeekRow = {
  round: number;
  minutes: number;
  goals: number;
  assists: number;
  expected_goals: number;
  expected_assists: number;
  was_home: boolean;
};
type FplPlayer = {
  code: number;
  name: string;
  team: string;
  position_group: string;
  age: number | null;
  minutes: number;
  starts: number;
  goals: number;
  assists: number;
  expected_goals: number;
  expected_assists: number;
  yellow_cards: number;
  red_cards: number;
  clean_sheets: number;
  saves: number;
  game_price: number;
  form: number;
  status: string;
  status_label: string;
  news: string | null;
  news_added: string | null;
  chance_of_playing: number | null;
  event_profile_player_id: number | null;
  rankings: Record<string, Ranking>;
  seasons: SeasonRow[];
  gameweeks: WeekRow[];
};
type Meta = {
  gameweek: number;
  minimum_minutes_for_rankings: number;
  source_note: string;
  summary_available?: boolean;
};

const POSITIONS: Record<string, string> = {
  GK: "Goalkeeper",
  DF: "Defender",
  MD: "Midfielder",
  FW: "Forward",
};

export default function FplProfilePage() {
  const { code } = useParams<{ code: string }>();
  const [payload, setPayload] = useState<Envelope<FplPlayer> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setPayload(null);
    setError("");
    void fetch(`${API}/fpl/players/${code}`, { signal: controller.signal })
      .then(async (response) => {
        if (response.status === 404)
          throw new Error("This player is not in the current Premier League feed.");
        if (!response.ok) throw new Error("The Premier League feed is unavailable right now.");
        return response.json() as Promise<Envelope<FplPlayer>>;
      })
      .then(setPayload)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Could not load this player.");
      });
    return () => controller.abort();
  }, [code]);

  if (error)
    return (
      <main className="product-page" id="workspace-content">
        <a className="text-link" href="/players">
          ← Player directory
        </a>
        <div className="notice">{error}</div>
      </main>
    );
  if (!payload)
    return (
      <main className="product-page" id="workspace-content">
        <PageLoader label="Loading current Premier League stats…" />
      </main>
    );

  const player = payload.data;
  const meta = payload.meta as unknown as Meta;
  const rankings = Object.entries(player.rankings);
  const unavailable = player.status !== "a";
  return (
    <main className="product-page" id="workspace-content">
      <a className="text-link" href="/players">
        ← Player directory
      </a>
      <header className="profile-header">
        <div className="profile-avatar">{player.name.slice(0, 2).toUpperCase()}</div>
        <div>
          <div className="eyebrow">Current stats profile</div>
          <h1>{player.name}</h1>
          <div className="identity-row">
            <span>{player.team}</span>
            <span>{POSITIONS[player.position_group] ?? player.position_group}</span>
            <span>{player.age ? `${player.age} years` : "Age unavailable"}</span>
            <span>Premier League 2026/27 · gameweek {meta.gameweek}</span>
          </div>
        </div>
        <span className="coverage-pill">● Stats tier</span>
      </header>

      <div className={`availability-banner ${unavailable ? "warn" : ""}`}>
        <strong>{player.status_label}</strong>
        {player.chance_of_playing !== null && !(player.news ?? "").includes("%")
          ? ` · ${player.chance_of_playing}% chance of playing next round`
          : ""}
        {player.news ? ` · ${player.news}` : ""}
        <small>
          Live from the Premier League feed{player.news_added ? `, updated ${new Date(player.news_added).toLocaleDateString("en-GB")}` : ""}.
        </small>
      </div>

      <div className="insight">
        <strong>What this profile is: </strong>
        current-season totals, expected stats and availability from the public Premier League
        feed. It has no event locations, so there are no heatmaps, pass maps, xT or archetypes.
        {player.event_profile_player_id ? (
          <>
            {" "}
            An older event-level profile exists:{" "}
            <a className="text-link" href={`/players/${player.event_profile_player_id}`}>
              open the full event profile →
            </a>
          </>
        ) : null}
      </div>

      <section className="stat-grid">
        <div className="stat">
          <small>Minutes</small>
          <strong>{formatNumber(player.minutes, 0)}</strong>
          <small>{player.starts} starts</small>
        </div>
        {player.position_group === "GK" ? (
          <>
            <div className="stat">
              <small>Saves</small>
              <strong>{player.saves}</strong>
            </div>
            <div className="stat">
              <small>Clean sheets</small>
              <strong>{player.clean_sheets}</strong>
            </div>
          </>
        ) : (
          <>
            <div className="stat">
              <small>Goals</small>
              <strong>{player.goals}</strong>
              <small>{formatNumber(player.expected_goals, 2)} xG</small>
            </div>
            <div className="stat">
              <small>Assists</small>
              <strong>{player.assists}</strong>
              <small>{formatNumber(player.expected_assists, 2)} xA</small>
            </div>
          </>
        )}
        <div className="stat">
          <small>Cards</small>
          <strong>
            {player.yellow_cards}Y {player.red_cards}R
          </strong>
        </div>
      </section>

      <section className="panel">
        <div className="card-top">
          <div>
            <div className="eyebrow">Ranked against current Premier League players</div>
            <h2>How the numbers compare</h2>
          </div>
          <span className="tag">Per 90 · same position</span>
        </div>
        {rankings.length ? (
          <>
            <div className="percentile-list">
              {rankings.map(([key, item]) => (
                <div className="percentile-row rank-row" key={key}>
                  <span>{item.label}</span>
                  <div className="fit-track light">
                    <i style={{ width: `${Math.max(2, item.percentile)}%` }} />
                  </div>
                  <b>
                    {formatNumber(item.value, 2)} · {ordinal(item.percentile)}
                  </b>
                </div>
              ))}
            </div>
            <p className="research-note">
              Ranked among {rankings[0][1].cohort_size} {POSITIONS[player.position_group]?.toLowerCase()}s with
              at least {meta.minimum_minutes_for_rankings} minutes so far. Early in the season these cohorts
              are small, so treat the rankings as provisional.
            </p>
          </>
        ) : (
          <EmptyState title="Not enough minutes to rank yet">
            Rankings need at least {meta.minimum_minutes_for_rankings} minutes this season.
          </EmptyState>
        )}
      </section>

      <section className="panel">
        <div className="eyebrow">Career in the Premier League</div>
        <h2>Season by season</h2>
        {player.seasons.length ? (
          <div className="table-wrap">
            <table className="transfer-table">
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Minutes</th>
                  <th>Goals</th>
                  <th>xG</th>
                  <th>Assists</th>
                  <th>xA</th>
                </tr>
              </thead>
              <tbody>
                {[...player.seasons].reverse().map((row) => (
                  <tr key={row.season}>
                    <td>{row.season}</td>
                    <td>{formatNumber(row.minutes, 0)}</td>
                    <td>{row.goals}</td>
                    <td>{row.expected_goals ?? "—"}</td>
                    <td>{row.assists}</td>
                    <td>{row.expected_assists ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No previous Premier League seasons">
            This player has no earlier seasons in the feed, or the history could not be loaded.
          </EmptyState>
        )}
        <p className="research-note">
          Expected stats appear only for seasons where the feed records them. Seasons before the
          player joined the Premier League are not included.
        </p>
      </section>

      {player.gameweeks.length ? (
        <section className="panel">
          <div className="eyebrow">This season</div>
          <h2>Gameweek by gameweek</h2>
          <div className="table-wrap">
            <table className="transfer-table">
              <thead>
                <tr>
                  <th>GW</th>
                  <th>Minutes</th>
                  <th>Goals</th>
                  <th>xG</th>
                  <th>Assists</th>
                  <th>xA</th>
                </tr>
              </thead>
              <tbody>
                {[...player.gameweeks].reverse().map((row) => (
                  <tr key={row.round}>
                    <td>{row.round}</td>
                    <td>{row.minutes}</td>
                    <td>{row.goals}</td>
                    <td>{row.expected_goals}</td>
                    <td>{row.assists}</td>
                    <td>{row.expected_assists}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <p className="research-note">
        {meta.source_note} (Fantasy-game price shown by the feed: £{player.game_price.toFixed(1)}m.)
      </p>
    </main>
  );
}
