"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API, EmptyState, formatNumber, ordinal, ShotMap, PitchHeatmap } from "../components";
import { InlineLoader, StatusMessage } from "../page-loader";

type Team = { team_id: number; name: string; players: number };
type League = { league_id: number; league_name: string; season: string; teams: Team[] };
type Member = {
  player_id: number;
  name: string;
  position_group: string;
  role: string | null;
  shirt_number: number | null;
  nationality: string | null;
  age: number | null;
  market_value_eur: number | null;
  injured: boolean;
  injury_return: string | null;
  rating: number | null;
  goals: number | null;
  assists: number | null;
  event_profile_player_id: number | null;
  current_stats_cached: boolean;
  minutes: number | null;
  position_codes: string | null;
};
type Lineup = {
  formation: string;
  starters: { player_id: number; x: number; y: number }[];
  bench: number[];
};
type Squad = {
  team_id: number;
  name: string;
  league_name: string;
  season: string;
  players: Member[];
  lineup: Lineup;
};
type Stat = {
  key: string;
  title: string;
  group: string;
  value: string | null;
  per90: number | null;
  percentile_per90: number | null;
};
type Profile = {
  player_id: number;
  name: string;
  team_id: number | null;
  team: string | null;
  birth_date: string | null;
  contract_end: string | null;
  height: string | null;
  foot: string | null;
  positions: { label: string; short: string; main: boolean }[];
  league: { name: string | null; season: string | null; stats: Record<string, number | string> };
  traits: { title: string; items: { key: string; title: string; value: number }[] } | null;
  stats: Stat[];
  market_values: { date: string; value: number }[];
  heatmap: [number, number][];
  shots: { x: number; y: number; minute: number; xg: number | null; type: string }[];
  squad: { event_profile_player_id: number | null; link_basis: string | null } | null;
};
type Gap = { stat: string; target_per90: number; candidate_per90: number; percentile_gap: number };
type Candidate = {
  player_id: number;
  name: string;
  team: string | null;
  position: string | null;
  minutes: number;
  market_value_eur: number | null;
  similarity: number;
  overall_difference: number;
  stats_compared: number;
  better_at: Gap[];
  weaker_at: Gap[];
};
type EventSimilar = Record<string, unknown>;
type Alternatives = {
  status: string;
  family?: string;
  target_minutes?: number;
  pool_size: number;
  minimum_minutes?: number;
  similar: Candidate[];
  upgrades: Candidate[];
  event_similar: EventSimilar[];
};

const GROUP_LABEL: Record<string, string> = {
  GK: "Goalkeepers",
  DF: "Defenders",
  MD: "Midfielders",
  FW: "Forwards",
};

function shortName(name: string) {
  const parts = name.split(" ");
  return parts.length > 1 ? parts.slice(1).join(" ") : name;
}
const FAMILY_LABEL: Record<string, string> = {
  keepers: "goalkeepers",
  fullbacks: "full-backs",
  center_backs: "centre-backs",
  midfielders: "midfielders",
  att_mid_wingers: "attacking midfielders and wingers",
  forwards: "forwards",
};
const BUDGETS = [
  ["", "Any value"],
  ["10000000", "Up to €10m"],
  ["25000000", "Up to €25m"],
  ["50000000", "Up to €50m"],
  ["100000000", "Up to €100m"],
];

function euros(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  if (value >= 1e6) return `€${(value / 1e6).toFixed(value >= 1e7 ? 0 : 1)}m`;
  return `€${Math.round(value / 1e3)}k`;
}

function heatCells(points: [number, number][]) {
  const columns = 12;
  const rows = 8;
  const counts = new Map<string, number>();
  for (const [x, y] of points) {
    const col = Math.min(columns - 1, Math.max(0, Math.floor((x / 105) * columns)));
    const row = Math.min(rows - 1, Math.max(0, Math.floor((y / 68) * rows)));
    counts.set(`${col}-${row}`, (counts.get(`${col}-${row}`) ?? 0) + 1);
  }
  return [...counts.entries()].map(([key, events]) => {
    const [x, y] = key.split("-").map(Number);
    return { x_bin: x, y_bin: y, events };
  });
}

export default function SquadsPage() {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [leagueId, setLeagueId] = useState<number | null>(null);
  const [squad, setSquad] = useState<Squad | null>(null);
  const [playerId, setPlayerId] = useState<number | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [alts, setAlts] = useState<Alternatives | null>(null);
  const [budget, setBudget] = useState("");
  const [message, setMessage] = useState("Loading clubs…");
  const [profileState, setProfileState] = useState("");
  const [compare, setCompare] = useState<Candidate | null>(null);
  const [compareProfile, setCompareProfile] = useState<Profile | null>(null);
  const [compareState, setCompareState] = useState("");
  const modalRef = useRef<HTMLElement | null>(null);
  const closeModal = useCallback(() => {
    setPlayerId(null);
    setProfile(null);
    setAlts(null);
    setCompare(null);
  }, []);

  useEffect(() => {
    if (playerId === null) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeModal();
    };
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [playerId, closeModal]);

  useEffect(() => {
    setCompare(null);
  }, [playerId]);

  useEffect(() => {
    if (compare === null) {
      setCompareProfile(null);
      setCompareState("");
      return;
    }
    const controller = new AbortController();
    setCompareProfile(null);
    setCompareState("Reading the other player's page…");
    void fetch(`${API}/squads/players/${compare.player_id}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("unavailable");
        return response.json() as Promise<{ data: Profile }>;
      })
      .then((payload) => {
        setCompareProfile(payload.data);
        setCompareState("");
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setCompareState("That player's page could not be read right now.");
      });
    return () => controller.abort();
  }, [compare]);

  useEffect(() => {
    modalRef.current?.querySelectorAll(".modal-left, .modal-right").forEach((column) => {
      column.scrollTo({ top: 0 });
    });
  }, [playerId]);

  useEffect(() => {
    void fetch(`${API}/squads/leagues`)
      .then((response) => response.json())
      .then((payload: { data: League[] }) => {
        setLeagues(payload.data);
        setLeagueId(payload.data[0]?.league_id ?? null);
        setMessage(payload.data.length ? "" : "No squads loaded yet. Run load-fotmob-squads.");
      })
      .catch(() => setMessage("Squad data is temporarily unavailable. Check the API connection."));
  }, []);

  const league = leagues.find((item) => item.league_id === leagueId);

  function openTeam(teamId: number) {
    setSquad(null);
    setPlayerId(null);
    setProfile(null);
    setAlts(null);
    void fetch(`${API}/squads/teams/${teamId}`)
      .then((response) => response.json())
      .then((payload: { data: Squad }) => setSquad(payload.data))
      .catch(() => setMessage("Could not load this squad."));
  }

  useEffect(() => {
    if (playerId === null) return;
    const controller = new AbortController();
    setProfile(null);
    setAlts(null);
    setProfileState("Reading the player page… the first visit to a player takes a few seconds.");
    void fetch(`${API}/squads/players/${playerId}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("unavailable");
        return response.json() as Promise<{ data: Profile }>;
      })
      .then((payload) => {
        setProfile(payload.data);
        setProfileState("");
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setProfileState("This player's page could not be read right now.");
      });
    return () => controller.abort();
  }, [playerId]);

  useEffect(() => {
    if (playerId === null) return;
    const controller = new AbortController();
    setAlts(null);
    const query = budget ? `?max_value_eur=${budget}` : "";
    void fetch(`${API}/squads/players/${playerId}/alternatives${query}`, {
      signal: controller.signal,
    })
      .then((response) => response.json() as Promise<{ data: Alternatives }>)
      .then((payload) => setAlts(payload.data))
      .catch(() => undefined);
    return () => controller.abort();
  }, [playerId, budget]);

  const statGroups = useMemo(() => {
    const groups: Record<string, Stat[]> = {};
    for (const stat of profile?.stats ?? []) {
      if (["Discipline"].includes(stat.group)) continue;
      (groups[stat.group] ??= []).push(stat);
    }
    return groups;
  }, [profile]);

  return (
    <main className="product-page" id="workspace-content">
      <div className="page-head">
        <div>
          <div className="eyebrow">Current squads</div>
          <h1 className="page-title">Club squads and alternatives</h1>
          <p className="lede">
            Pick a club, open a player, and see who plays a similar role and who ranks higher on
            this season&apos;s numbers.
          </p>
        </div>
        <span className="tag">Top five leagues · {league?.season ?? "2026/2027"}</span>
      </div>
      <StatusMessage message={message} />

      <div className="league-tabs" role="tablist" aria-label="League">
        {leagues.map((item) => (
          <button
            key={item.league_id}
            role="tab"
            aria-selected={item.league_id === leagueId}
            className={item.league_id === leagueId ? "active" : ""}
            onClick={() => setLeagueId(item.league_id)}
          >
            {item.league_name}
          </button>
        ))}
      </div>
      <div className="club-grid">
        {league?.teams.map((team) => (
          <button
            key={team.team_id}
            className={squad?.team_id === team.team_id ? "club active" : "club"}
            onClick={() => openTeam(team.team_id)}
          >
            <ClubCrest teamId={team.team_id} size={28} />
            <span>
              {team.name}
              <small>{team.players} players</small>
            </span>
          </button>
        ))}
      </div>

      {squad ? (
        <section className="panel squad-panel" aria-label={`${squad.name} lineup`}>
          <div className="card-top">
            <div>
              <div className="eyebrow">
                {squad.league_name} · {squad.season}
              </div>
              <h2 className="club-title">
                <ClubCrest teamId={squad.team_id} size={36} />
                {squad.name}
              </h2>
            </div>
            <span className="tag">Likely XI · {squad.lineup.formation}</span>
          </div>
          <SquadPitch squad={squad} activeId={playerId} onOpen={setPlayerId} />
          <p className="research-note">
            Estimated from minutes played this season and each player&apos;s listed positions. It shows who
            has played most, not an official team sheet. Click any player for the full profile.
          </p>
          <BenchList squad={squad} activeId={playerId} onOpen={setPlayerId} />
        </section>
      ) : null}

      {playerId !== null ? (
        <div className="modal-backdrop" onMouseDown={closeModal}>
          <section
            className="panel player-panel modal"
            role="dialog"
            aria-modal="true"
            aria-label={profile ? `${profile.name} profile` : "Player profile"}
            ref={modalRef}
            onMouseDown={(event) => event.stopPropagation()}
          >
          <button className="modal-close" aria-label="Close player profile" onClick={closeModal}>
            ×
          </button>
          {profileState ? <div className="notice">{profileState}</div> : null}
          {profile && !compare ? (
            <div className="modal-head">
              <div className="card-top">
                <div className="modal-identity">
                <ModalPhoto playerId={profile.player_id} name={profile.name} teamId={profile.team_id} />
                <div>
                  <div className="eyebrow">
                    {profile.team ?? "Club unavailable"} ·{" "}
                    {profile.positions.find((p) => p.main)?.label ?? profile.positions[0]?.label ?? "Position unclear"}
                  </div>
                  <h2>{profile.name}</h2>
                  <p className="analysis-copy">
                    {[
                      profile.birth_date ? `born ${profile.birth_date}` : null,
                      profile.height,
                      profile.foot ? `${profile.foot} foot` : null,
                      profile.contract_end ? `contract to ${profile.contract_end.slice(0, 4)}` : null,
                      profile.market_values.length
                        ? `value ${euros(profile.market_values[profile.market_values.length - 1].value)}`
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                </div>
                <span className="coverage-pill">● Current stats · FotMob</span>
              </div>
              {profile.squad?.event_profile_player_id ? (
                <p className="insight">
                  An older event-level profile exists for this player:{" "}
                  <a className="text-link" href={`/players/${profile.squad.event_profile_player_id}`}>
                    open the full event profile →
                  </a>
                </p>
              ) : null}
            </div>
          ) : null}
          {compare ? (
            <ComparisonView
              target={profile}
              candidate={compareProfile}
              row={compare}
              state={compareState}
              onBack={() => setCompare(null)}
              onOpen={() => setPlayerId(compare.player_id)}
            />
          ) : (
          <div className="modal-body">
            <div className="modal-left">
              {profile ? (
                <>
              {profile.traits ? (
                <div className="trait-block">
                  <h3>{profile.traits.title}</h3>
                  {profile.traits.items.map((item) => (
                    <div className="percentile-row rank-row" key={item.key}>
                      <span>{item.title}</span>
                      <div className="fit-track light">
                        <i style={{ width: `${Math.max(2, item.value * 100)}%` }} />
                      </div>
                      <b>{ordinal(item.value * 100)}</b>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="viz-pair">
                {profile.heatmap.length ? (
                  <PitchHeatmap
                    cells={heatCells(profile.heatmap)}
                    events={profile.heatmap.length}
                    caption="Where this player was involved this season. Coordinates come from FotMob's heat map."
                  />
                ) : null}
                {profile.shots.length ? (
                  <ShotMap
                    shots={profile.shots.map((shot) => ({
                      x_m: shot.x,
                      y_m: shot.y,
                      outcome: shot.type,
                      shot_xg: shot.xg,
                    }))}
                  />
                ) : null}
              </div>
              {Object.entries(statGroups).map(([group, stats]) => (
                <details className="stat-details" key={group}>
                  <summary>
                    {group} · {stats.length} stats
                  </summary>
                  {stats.map((stat) => (
                    <div className="percentile-row rank-row" key={stat.key}>
                      <span>{stat.title}</span>
                      <div className="fit-track light">
                        <i style={{ width: `${Math.max(2, stat.percentile_per90 ?? 0)}%` }} />
                      </div>
                      <b>
                        {stat.per90 !== null ? formatNumber(stat.per90, 2) : "—"} ·{" "}
                        {stat.percentile_per90 !== null ? ordinal(stat.percentile_per90) : "—"}
                      </b>
                    </div>
                  ))}
                </details>
              ))}
              <p className="research-note">
                Per-90 values this season. Percentiles are FotMob&apos;s own, against its comparison group.
              </p>
                </>
              ) : null}
            </div>
            <div className="modal-right">
          <div className="alt-head">
            <div>
              <div className="eyebrow">Alternatives</div>
              <h2>Similar players and possible upgrades</h2>
            </div>
            <label>
              Market value
              <select value={budget} onChange={(event) => setBudget(event.target.value)}>
                {BUDGETS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {alts === null ? <div className="notice">Finding alternatives…</div> : null}
          {alts && alts.status !== "OK" ? (
            <EmptyState title="No comparison yet">
              {alts.status === "TARGET_TOO_FEW_MINUTES"
                ? `This player needs at least ${alts.minimum_minutes} minutes this season to be compared.`
                : "This player's current stats are not available to compare."}
            </EmptyState>
          ) : null}
          {alts && alts.status === "OK" ? (
            <>
              <p className="research-note">
                Compared with {alts.pool_size} current {FAMILY_LABEL[alts.family ?? ""] ?? "players"}{" "}
                across the top five leagues who have played at least {alts.minimum_minutes} minutes.
                This describes measured output this season, not how a player would fit another team.
              </p>
              {alts.target_minutes !== undefined && alts.target_minutes < 450 ? (
                <p className="insight">
                  Only {alts.target_minutes} minutes so far for this player, so the comparison is
                  provisional. A few matches can swing every number.
                </p>
              ) : null}
              <p className="research-note">Click a player to compare the two side by side.</p>
              <AltList
                title="Possible upgrades"
                empty="Nobody similar ranks clearly higher on these numbers."
                rows={alts.upgrades}
                onOpen={setCompare}
              />
              <AltList
                title="Most similar profiles"
                empty="No close matches yet."
                rows={alts.similar}
                onOpen={setCompare}
              />
              {alts.event_similar.length ? (
                <div className="alt-block">
                  <h3>Older event-data matches (historic seasons)</h3>
                  {alts.event_similar.map((row, index) => (
                    <a
                      className="alt-row"
                      key={index}
                      href={`/players/${String(row.player_id)}`}
                    >
                      <span className="who">
                        <b>{String(row.name ?? row.player_id)}</b>
                        <small>
                          {String(row.team_name ?? "")} · {String(row.season_label ?? "")}
                        </small>
                      </span>
                      <span className="scores">
                        <span>{formatNumber(row.recommendation_score, 0)}% alike</span>
                      </span>
                    </a>
                  ))}
                  <p className="research-note">
                    These come from the open event dataset (mostly 2015/16 and 2017/18), so they show
                    style, not who is available now.
                  </p>
                </div>
              ) : null}
            </>
          ) : null}
            </div>
          </div>
          )}
          </section>
        </div>
      ) : null}
    </main>
  );
}

function AltList({
  title,
  rows,
  empty,
  onOpen,
}: {
  title: string;
  rows: Candidate[];
  empty: string;
  onOpen: (row: Candidate) => void;
}) {
  return (
    <div className="alt-block">
      <h3>{title}</h3>
      {rows.length ? (
        rows.map((row) => (
          <button className="alt-row" key={row.player_id} onClick={() => onOpen(row)}>
            <span className="who">
              <b>{row.name}</b>
              <small>
                {row.team ?? "Club unavailable"} · {row.position ?? ""} · {euros(row.market_value_eur)}
              </small>
            </span>
            <span className="scores">
              <span>{row.similarity.toFixed(0)}% alike</span>
              <span className={row.overall_difference >= 0 ? "up" : "down"}>
                {row.overall_difference >= 0 ? "+" : ""}
                {row.overall_difference.toFixed(1)} on key strengths
              </span>
            </span>
            <span className="gaps">
              {row.better_at.length ? (
                <span>
                  Better: {row.better_at.map((gap) => `${gap.stat} (${gap.candidate_per90} vs ${gap.target_per90})`).join(", ")}
                </span>
              ) : null}
              {row.weaker_at.length ? (
                <span>
                  Weaker: {row.weaker_at.map((gap) => `${gap.stat} (${gap.candidate_per90} vs ${gap.target_per90})`).join(", ")}
                </span>
              ) : null}
            </span>
          </button>
        ))
      ) : (
        <p className="research-note">{empty}</p>
      )}
    </div>
  );
}

function SquadPitch({
  squad,
  activeId,
  onOpen,
}: {
  squad: Squad;
  activeId: number | null;
  onOpen: (id: number) => void;
}) {
  const byId = new Map(squad.players.map((member) => [member.player_id, member]));
  return (
    <div className="lineup-pitch" role="group" aria-label={`${squad.name} likely starting XI`}>
      <div className="lp-half" />
      <div className="lp-circle" />
      <div className="lp-box lp-top" />
      <div className="lp-box lp-bottom" />
      {squad.lineup.starters.map((slot) => {
        const member = byId.get(slot.player_id);
        if (!member) return null;
        return (
          <button
            key={slot.player_id}
            className={slot.player_id === activeId ? "slot active" : "slot"}
            style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
            onClick={() => onOpen(slot.player_id)}
            aria-label={`${member.name}, ${member.role ?? ""}. Open profile`}
          >
            <span className={member.injured ? "dot injured" : "dot"}>
              <PlayerPhoto playerId={member.player_id} fallback={member.shirt_number ?? "–"} />
              {member.shirt_number != null ? <i className="dot-number">{member.shirt_number}</i> : null}
            </span>
            <b>{shortName(member.name)}</b>
            <small>{euros(member.market_value_eur)}</small>
            {member.injured ? <em>Injured</em> : null}
          </button>
        );
      })}
    </div>
  );
}

function BenchList({
  squad,
  activeId,
  onOpen,
}: {
  squad: Squad;
  activeId: number | null;
  onOpen: (id: number) => void;
}) {
  const byId = new Map(squad.players.map((member) => [member.player_id, member]));
  const bench = squad.lineup.bench
    .map((id) => byId.get(id))
    .filter((member): member is Member => member !== undefined);
  if (!bench.length) return null;
  return (
    <div className="bench">
      <h3>Rest of the squad</h3>
      <div className="bench-grid">
        {bench.map((member) => (
          <button
            key={member.player_id}
            className={member.player_id === activeId ? "bench-item active" : "bench-item"}
            onClick={() => onOpen(member.player_id)}
          >
            <span className="bench-photo">
              <PlayerPhoto playerId={member.player_id} fallback={member.shirt_number ?? "–"} />
            </span>
            <span className="who">
              <b>{member.name}</b>
              <small>
                {member.shirt_number != null ? `#${member.shirt_number} · ` : ""}
                {GROUP_LABEL[member.position_group]?.replace(/s$/, "") ?? ""}
                {member.age ? ` · ${member.age}` : ""}
                {member.minutes ? ` · ${member.minutes} min` : ""}
              </small>
            </span>
            <span className="meta">
              {member.injured ? <em className="injury">Injured</em> : null}
              {member.event_profile_player_id ? <em className="badge">event profile</em> : null}
              <span>{euros(member.market_value_eur)}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

/** Player headshot from FotMob's image CDN; falls back to the shirt number if there is no photo. */
function PlayerPhoto({ playerId, fallback }: { playerId: number; fallback: string | number }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <span className="photo-fallback">{fallback}</span>;
  return (
    <img
      className="player-photo"
      src={`https://images.fotmob.com/image_resources/playerimages/${playerId}.png`}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

/** Club crest from FotMob's image CDN (same source as the squads); hidden if it fails to load. */
function ClubCrest({ teamId, size }: { teamId: number; size: number }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <span className="club-crest placeholder" style={{ width: size, height: size }} />;
  return (
    <img
      className="club-crest"
      src={`https://images.fotmob.com/image_resources/logo/teamlogo/${teamId}${size > 32 ? "" : "_small"}.png`}
      alt=""
      width={size}
      height={size}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

const LOWER_IS_BETTER = new Set(["dispossessed", "dribbled_past", "fouls", "error_led_to_goal"]);
const SKIPPED_GROUPS = new Set(["Discipline"]);

function better(key: string, a: number | null, b: number | null): "a" | "b" | "tie" {
  if (a === null || b === null) return "tie";
  const spread = Math.abs(a - b);
  if (spread < Math.max(0.03, 0.05 * Math.max(Math.abs(a), Math.abs(b)))) return "tie";
  const aWins = LOWER_IS_BETTER.has(key) ? a < b : a > b;
  return aWins ? "a" : "b";
}

function bio(profile: Profile) {
  return [
    profile.birth_date ? `born ${profile.birth_date}` : null,
    profile.height,
    profile.foot ? `${profile.foot} foot` : null,
    profile.contract_end ? `contract to ${profile.contract_end.slice(0, 4)}` : null,
    profile.market_values.length
      ? `value ${euros(profile.market_values[profile.market_values.length - 1].value)}`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function ComparisonView({
  target,
  candidate,
  row,
  state,
  onBack,
  onOpen,
}: {
  target: Profile | null;
  candidate: Profile | null;
  row: Candidate;
  state: string;
  onBack: () => void;
  onOpen: () => void;
}) {
  const groups = useMemo(() => {
    const result: Record<string, { key: string; title: string; a: Stat; b: Stat | undefined }[]> = {};
    if (!target) return result;
    const theirs = new Map((candidate?.stats ?? []).map((stat) => [stat.key, stat]));
    for (const stat of target.stats) {
      if (SKIPPED_GROUPS.has(stat.group)) continue;
      (result[stat.group] ??= []).push({
        key: stat.key,
        title: stat.title,
        a: stat,
        b: theirs.get(stat.key),
      });
    }
    return result;
  }, [target, candidate]);

  const tally = useMemo(() => {
    let a = 0;
    let b = 0;
    for (const rows of Object.values(groups)) {
      for (const item of rows) {
        const winner = better(item.key, item.a.per90, item.b?.per90 ?? null);
        if (winner === "a") a += 1;
        if (winner === "b") b += 1;
      }
    }
    return { a, b };
  }, [groups]);

  if (!target) return <div className="compare-body"><InlineLoader label="Loading comparison…" /></div>;
  return (
    <div className="compare-body">
      <div className="cmp-head">
        <div className="cmp-card">
          <div className="eyebrow">{target.team ?? ""}</div>
          <h3>{target.name}</h3>
          <p>{bio(target)}</p>
        </div>
        <div className="cmp-vs">
          <b>{row.similarity.toFixed(0)}% alike</b>
          <span className={row.overall_difference >= 0 ? "up" : "down"}>
            {row.overall_difference >= 0 ? "+" : ""}
            {row.overall_difference.toFixed(1)} on key strengths
          </span>
          {candidate ? (
            <small>
              {candidate.name.split(" ").slice(-1)[0]} ahead on {tally.b} stats ·{" "}
              {target.name.split(" ").slice(-1)[0]} ahead on {tally.a}
            </small>
          ) : null}
        </div>
        <div className="cmp-card right">
          <div className="eyebrow">{candidate?.team ?? row.team ?? ""}</div>
          <h3>{candidate?.name ?? row.name}</h3>
          <p>{candidate ? bio(candidate) : ""}</p>
        </div>
      </div>
      <div className="cmp-actions">
        <button className="cmp-button" onClick={onBack}>
          ← Back to alternatives
        </button>
        <button className="cmp-button primary" onClick={onOpen}>
          Open {row.name}&apos;s profile
        </button>
      </div>
      {state ? <div className="notice">{state}</div> : null}
      {candidate ? (
        <>
          <div className="cmp-maps">
            {[target, candidate].map((profile, index) => (
              <div key={index}>
                {profile.heatmap.length ? (
                  <PitchHeatmap
                    cells={heatCells(profile.heatmap)}
                    events={profile.heatmap.length}
                    caption={`${profile.name}: where the player was involved this season.`}
                  />
                ) : (
                  <p className="research-note">No heat map for {profile.name}.</p>
                )}
                {profile.shots.length ? (
                  <ShotMap
                    shots={profile.shots.map((shot) => ({
                      x_m: shot.x,
                      y_m: shot.y,
                      outcome: shot.type,
                      shot_xg: shot.xg,
                    }))}
                  />
                ) : null}
              </div>
            ))}
          </div>
          {target.traits && candidate.traits ? (
            <div className="cmp-section">
              <h3>Role ranking · FotMob</h3>
              {target.traits.items.map((item) => {
                const other = candidate.traits?.items.find((entry) => entry.key === item.key);
                return (
                  <div className="cmp-row" key={item.key}>
                    <span className="cmp-label">{item.title}</span>
                    <CmpCell value={`${ordinal(item.value * 100)}`} width={item.value * 100} win={other ? item.value > other.value : false} />
                    <CmpCell value={other ? `${ordinal(other.value * 100)}` : "—"} width={(other?.value ?? 0) * 100} win={other ? other.value > item.value : false} />
                  </div>
                );
              })}
            </div>
          ) : null}
          {Object.entries(groups).map(([group, items]) => (
            <div className="cmp-section" key={group}>
              <h3>{group}</h3>
              {items.map((item) => {
                const winner = better(item.key, item.a.per90, item.b?.per90 ?? null);
                return (
                  <div className="cmp-row" key={item.key}>
                    <span className="cmp-label">{item.title}</span>
                    <CmpCell
                      value={item.a.per90 !== null ? formatNumber(item.a.per90, 2) : "—"}
                      sub={item.a.percentile_per90 !== null ? ordinal(item.a.percentile_per90) : undefined}
                      width={item.a.percentile_per90 ?? 0}
                      win={winner === "a"}
                    />
                    <CmpCell
                      value={item.b?.per90 !== null && item.b?.per90 !== undefined ? formatNumber(item.b.per90, 2) : "—"}
                      sub={item.b?.percentile_per90 !== null && item.b?.percentile_per90 !== undefined ? ordinal(item.b.percentile_per90) : undefined}
                      width={item.b?.percentile_per90 ?? 0}
                      win={winner === "b"}
                    />
                  </div>
                );
              })}
            </div>
          ))}
          <p className="research-note">
            Per-90 values this season; the highlighted side is better on that stat (lower is better for
            fouls, dispossessed and dribbled past). Bars show FotMob&apos;s own percentile within its
            comparison group, so they are not directly comparable across leagues. Small differences are
            shown as ties.
          </p>
        </>
      ) : null}
    </div>
  );
}

function CmpCell({
  value,
  sub,
  width,
  win,
}: {
  value: string;
  sub?: string;
  width: number;
  win: boolean;
}) {
  return (
    <span className={win ? "cmp-cell win" : "cmp-cell"}>
      <span className="cmp-value">
        {value}
        {sub ? <small> · {sub}</small> : null}
      </span>
      <span className="cmp-track">
        <i style={{ width: `${Math.max(2, Math.min(100, width))}%` }} />
      </span>
    </span>
  );
}

/** Player headshot from FotMob's image CDN, with the club crest badge; initials if no photo. */
function ModalPhoto({ playerId, name, teamId }: { playerId: number; name: string; teamId?: number | null }) {
  const [failed, setFailed] = useState(false);
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <div className="modal-photo">
      {failed ? (
        <span className="modal-photo-initials">{initials}</span>
      ) : (
        <img
          src={`https://images.fotmob.com/image_resources/playerimages/${playerId}.png`}
          alt={name}
          width={96}
          height={96}
          onError={() => setFailed(true)}
        />
      )}
      {teamId ? (
        <span className="modal-photo-crest">
          <ClubCrest teamId={teamId} size={28} />
        </span>
      ) : null}
    </div>
  );
}
