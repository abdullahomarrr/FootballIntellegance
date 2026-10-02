"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { API, EmptyState, Envelope, formatNumber, ordinal } from "../../../components";
import { PageLoader } from "../../../page-loader";

type Ranking = { label: string; value: number; percentile: number; cohort_size: number };
type LaligaPlayer = {
  id: string;
  name: string;
  team: string;
  club_unclear: boolean;
  feed_club: string | null;
  position_group: string;
  appearances: number;
  starts: number;
  minutes: number;
  goals: number;
  assists: number;
  shots: number;
  shots_on_target: number;
  key_passes: number;
  passes: number;
  pass_completion: number | null;
  tackles: number;
  interceptions: number;
  saves: number;
  yellow_cards: number;
  red_cards: number;
  average_rating: number | null;
  event_profile_player_id: number | null;
  link_basis: string | null;
  rankings: Record<string, Ranking>;
};
type Meta = {
  season: string;
  matches_covered: number;
  minimum_minutes_for_rankings: number;
  source_note: string;
};

const POSITIONS: Record<string, string> = {
  GK: "Goalkeeper",
  DF: "Defender",
  MD: "Midfielder",
  FW: "Forward",
};

function plural(count: number, one: string, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
}

export default function LaligaProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [payload, setPayload] = useState<Envelope<LaligaPlayer> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setPayload(null);
    setError("");
    void fetch(`${API}/laliga/players/${id}`, { signal: controller.signal })
      .then(async (response) => {
        if (response.status === 404)
          throw new Error("This player has no minutes in the current La Liga season data.");
        if (!response.ok) throw new Error("The La Liga feed is unavailable right now.");
        return response.json() as Promise<Envelope<LaligaPlayer>>;
      })
      .then(setPayload)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Could not load this player.");
      });
    return () => controller.abort();
  }, [id]);

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
        <PageLoader label="Loading current La Liga stats…"><small className="page-loader-hint">The first load can take a minute.</small></PageLoader>
      </main>
    );

  const player = payload.data;
  const meta = payload.meta as unknown as Meta;
  const rankings = Object.entries(player.rankings);
  const keeper = player.position_group === "GK";
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
            <span>{player.club_unclear ? "Club unclear" : player.team}</span>
            <span>{POSITIONS[player.position_group] ?? "Position unclear"}</span>
            <span>
              La Liga {meta.season} · {meta.matches_covered} matches covered
            </span>
          </div>
        </div>
        <span className="coverage-pill">● Stats tier</span>
      </header>

      <div className="insight">
        <strong>What this profile is: </strong>
        season totals summed from each match&apos;s player lines, from a free third-party feed. It has
        no event locations, expected stats or birth dates, so there are no heatmaps, pass maps, xT or
        archetypes.
        {player.club_unclear ? (
          <>
            {" "}
            {player.feed_club
              ? `The feed lists this player's current club as ${player.feed_club}, which is not a La Liga side,`
              : "The feed gives no current club for this player,"}{" "}
            so the club they played these matches for is unclear.
          </>
        ) : null}
        {player.event_profile_player_id ? (
          <>
            {" "}
            An older event-level profile exists (matched by exact name and club):{" "}
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
          <small>
            {plural(player.appearances, "appearance")} · {plural(player.starts, "start")}
          </small>
        </div>
        {keeper ? (
          <div className="stat">
            <small>Saves</small>
            <strong>{player.saves}</strong>
          </div>
        ) : (
          <>
            <div className="stat">
              <small>Goals</small>
              <strong>{player.goals}</strong>
              <small>
                {plural(player.shots, "shot")} · {player.shots_on_target} on target
              </small>
            </div>
            <div className="stat">
              <small>Assists</small>
              <strong>{player.assists}</strong>
              <small>{plural(player.key_passes, "key pass", "key passes")}</small>
            </div>
          </>
        )}
        <div className="stat">
          <small>Average rating</small>
          <strong>{player.average_rating !== null ? formatNumber(player.average_rating, 2) : "—"}</strong>
          <small>
            {player.pass_completion !== null
              ? `${formatNumber(player.pass_completion, 1)}% pass completion`
              : "pass completion needs 100+ passes"}
          </small>
        </div>
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
            <div className="eyebrow">Ranked against current La Liga players</div>
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
              Ranked among up to {Math.max(...rankings.map(([, item]) => item.cohort_size))}{" "}
              {POSITIONS[player.position_group]?.toLowerCase()}s with at least{" "}
              {meta.minimum_minutes_for_rankings} minutes so far. It is early in the season, so treat the
              rankings as provisional. Pass completion counts every pass the feed records, so
              goalkeepers who kick long score low on it.
            </p>
          </>
        ) : (
          <EmptyState title="Not enough minutes to rank yet">
            Rankings need at least {meta.minimum_minutes_for_rankings} minutes this season.
          </EmptyState>
        )}
      </section>

      <p className="research-note">{meta.source_note}</p>
    </main>
  );
}
