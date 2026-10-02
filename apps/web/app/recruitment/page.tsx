"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  API,
  EmptyState,
  Envelope,
  formatNumber,
  humanize,
  Methodology,
  Player,
  PlayerSearch,
} from "../components";
import { euros } from "../market-panel";
import { PageLoader } from "../page-loader";

type Difference = { target: number; candidate: number; difference: number };
type Similar = {
  player_id: number;
  name: string;
  team_name?: string;
  position_group?: string;
  similarity_score: number;
  recommendation_score?: number;
  role_fit_score?: number | null;
  minutes_played?: number;
  feature_differences?: Record<string, Difference>;
  compared_feature_count?: number;
  target_feature_count?: number;
  feature_coverage_pct?: number;
  confidence?: string;
  role_weighted_feature_count?: number;
  model_version?: string;
  competition_name?: string;
  season_label?: string;
  market_value_eur?: number | null;
};
type Role = {
  role_id: number;
  name: string;
  positions: string[];
  feature_weights: Record<string, number>;
  hard_constraints: Record<string, unknown>;
  feature_set_version?: string;
};
type Shortlist = {
  shortlist_id: number;
  name: string;
  status: string;
  role_name?: string;
  player_count: number;
};
const outfieldMetrics = [
  "pass_completion_pct",
  "pressured_pass_completion_pct",
  "progressive_passes_per_90",
  "passes_into_final_third_per_90",
  "box_entries_per_90",
  "progressive_carries_per_90",
  "successful_dribbles_per_90",
  "pressures_per_90",
  "recoveries_per_90",
  "defensive_actions_per_90",
  "defensive_duels_per_90",
  "turnovers_per_90",
  "xg_per_90",
  "average_shot_xg",
];
const goalkeeperMetrics = [
  "goalkeeper_saves_per_90",
  "goals_conceded_per_90",
  "claims_and_punches_per_90",
  "sweeper_actions_per_90",
];
const positionNames: Record<string, string> = {
  GK: "Goalkeeper",
  DF: "Defender",
  MD: "Midfielder",
  FW: "Forward",
};
const positionOrder = ["GK", "DF", "MD", "FW"];
function rolePriorities(role: Role) {
  return Object.entries(role.feature_weights)
    .filter(([, weight]) => weight > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([metric]) => humanize(metric).replace(/ Per 90$/i, "").replace(/ Pct$/i, " %").toLowerCase());
}
function rolePreset(name: string, position: string) {
  const metrics = position === "GK" ? goalkeeperMetrics : outfieldMetrics;
  const weights = Object.fromEntries(
    metrics.map((metric) => [metric, name === "Balanced profile" ? 3 : 0]),
  );
  const priorities: Record<string, string[]> = {
    "Progressive creator": [
      "progressive_passes_per_90",
      "passes_into_final_third_per_90",
      "box_entries_per_90",
    ],
    "Defensive reader": [
      "pressures_per_90",
      "recoveries_per_90",
      "defensive_actions_per_90",
      "defensive_duels_per_90",
    ],
    "Ball-carrying threat": [
      "progressive_carries_per_90",
      "successful_dribbles_per_90",
      "box_entries_per_90",
    ],
    "Shot prevention": ["goalkeeper_saves_per_90", "goals_conceded_per_90"],
    "Area control": ["claims_and_punches_per_90"],
    "Sweeper keeper": ["sweeper_actions_per_90"],
  };
  for (const metric of priorities[name] ?? [])
    if (metric in weights) weights[metric] = 5;
  return weights;
}

export default function RecruitmentPage() {
  const [player, setPlayer] = useState<Player | null>(null),
    [result, setResult] = useState<Envelope<Similar[]> | null>(null),
    [loading, setLoading] = useState(false),
    [error, setError] = useState("");
  const [maxValue, setMaxValue] = useState("");
  const [roles, setRoles] = useState<Role[]>([]),
    [lists, setLists] = useState<Shortlist[]>([]),
    [roleName, setRoleName] = useState(""),
    [position, setPosition] = useState("FW"),
    [minimumMinutes, setMinimumMinutes] = useState("900"),
    [maximumAge, setMaximumAge] = useState(""),
    [weights, setWeights] = useState<Record<string, number>>(
      rolePreset("Balanced profile", "FW"),
    ),
    [selectedRole, setSelectedRole] = useState(""),
    [selectedList, setSelectedList] = useState(""),
    [message, setMessage] = useState("");
  const roleMetrics = position === "GK" ? goalkeeperMetrics : outfieldMetrics;
  const playerPosition = player?.position_group ?? null;
  const availableRoles = playerPosition
    ? roles.filter((role) => role.positions.includes(playerPosition))
    : roles;
  const activeRole = roles.find((role) => String(role.role_id) === selectedRole) ?? null;
  async function loadWorkspace() {
    try {
      const [rr, sr] = await Promise.all([
        fetch(`${API}/recruitment/roles`),
        fetch(`${API}/shortlists`),
      ]);
      const [rp, sp] = await Promise.all([rr.json(), sr.json()]);
      setRoles(rp.data ?? []);
      setLists(
        (sp.data ?? []).filter((item: Shortlist) => item.status === "ACTIVE"),
      );
    } catch {
      setMessage("Saved roles and shortlists are temporarily unavailable.");
    }
  }
  useEffect(() => {
    void loadWorkspace();
  }, []);
  async function saveRole(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      const response = await fetch(`${API}/recruitment/roles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: roleName,
          positions: [position],
          feature_weights: weights,
          hard_constraints: {
            minimum_minutes: Number(minimumMinutes),
            ...(maximumAge ? { maximum_age: Number(maximumAge) } : {}),
          },
          feature_set_version: "event_intelligence_v1",
        }),
      });
      if (!response.ok) throw Error(`API returned ${response.status}`);
      setRoleName("");
      setMessage(
        "Recruitment role saved. It is now available when creating a shortlist.",
      );
      await loadWorkspace();
    } catch (e) {
      setMessage(
        `Could not save role: ${e instanceof Error ? e.message : "unknown error"}`,
      );
    }
  }
  async function run() {
    if (!player) return;
    setLoading(true);
    setError("");
    try {
      const query = selectedRole ? `?role_id=${selectedRole}` : "";
      const r = await fetch(
          `${API}/players/${player.player_id}/similar${query}`,
        ),
        p = await r.json();
      if (!r.ok) throw Error(p.detail ?? "Comparison unavailable");
      setResult(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comparison unavailable");
    } finally {
      setLoading(false);
    }
  }
  async function addCandidate(candidate: Similar, rank: number) {
    if (!selectedList) {
      setMessage("Choose an active shortlist before adding a candidate.");
      return;
    }
    const closest = Object.entries(candidate.feature_differences ?? {}).sort(
      (a, b) => Math.abs(a[1].difference) - Math.abs(b[1].difference),
    )[0];
    const roleEvidence =
      selectedRole && candidate.role_fit_score != null
        ? `; ${formatNumber(candidate.role_fit_score, 0)}/100 fit to ${roles.find((role) => String(role.role_id) === selectedRole)?.name ?? "the selected role"}`
        : "";
    const rationale = `${formatNumber(candidate.similarity_score, 0)}/100 advanced-event similarity to ${player?.canonical_name ?? "the reference profile"}${roleEvidence}${closest ? `; closest alignment: ${humanize(closest[0]).toLowerCase()}` : ""}. Requires video and live-scout review.`;
    const response = await fetch(`${API}/shortlists/${selectedList}/players`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_id: candidate.player_id,
        rank,
        stage: "IDENTIFIED",
        rationale,
        decision_evidence: {
          reference_player_id: player!.player_id,
        },
      }),
    });
    setMessage(
      response.ok
        ? `${candidate.name} added with an evidence-backed rationale.`
        : `Could not add ${candidate.name}; API returned ${response.status}.`,
    );
    if (response.ok) await loadWorkspace();
  }
  const limit = maxValue ? Number(maxValue) * 1_000_000 : null;
  const allCandidates = result?.data ?? [];
  const visibleCandidates =
    limit === null
      ? allCandidates
      : allCandidates.filter(
          (candidate) =>
            candidate.market_value_eur !== null &&
            candidate.market_value_eur !== undefined &&
            candidate.market_value_eur <= limit,
        );
  const hiddenByValue = allCandidates.length - visibleCandidates.length;
  return (
    <main className="product-page" id="workspace-content">
      <div className="page-head">
        <div>
          <div className="eyebrow">Recruitment planning</div>
          <h1 className="page-title">Recruitment search</h1>
          <p className="lede">
            Find players who play like someone you already rate, ranked for the role you
            need to fill.
          </p>
        </div>
      </div>
      <ol className="how-steps">
        <li>
          <b>Pick a player you like</b>
          <span>Their playing style becomes the template.</span>
        </li>
        <li>
          <b>Choose the role you&apos;re filling</b>
          <span>Optional. Ranks matches by what that role needs most.</span>
        </li>
        <li>
          <b>Review and shortlist</b>
          <span>See why each player matches, then save the ones worth scouting.</span>
        </li>
      </ol>
      <section className="panel">
        <div className="card-top">
          <div>
            <div className="eyebrow">Find alternatives</div>
            <h2>Who plays like this player?</h2>
          </div>
          <span className="tag">Compared within the same league, season and position</span>
        </div>
        <div className="workflow recruit-form">
          <div className="recruit-field">
          <PlayerSearch
            onSelect={(p) => {
              setPlayer(p);
              setResult(null);
              const current = roles.find((role) => String(role.role_id) === selectedRole);
              if (current && p.position_group && !current.positions.includes(p.position_group))
                setSelectedRole("");
            }}
            label="Reference player"
          />
            <small className="field-hint">
              {player
                ? `${player.canonical_name}${player.position_group ? ` · ${positionNames[player.position_group] ?? player.position_group}` : ""}`
                : "Whose playing style do you want more of?"}
            </small>
          </div>
          <label>
            Role you&apos;re filling
            <select
              value={selectedRole}
              onChange={(e) => {
                setSelectedRole(e.target.value);
                setResult(null);
              }}
            >
              <option value="">Any role (style match only)</option>
              {positionOrder
                .filter((group) => availableRoles.some((role) => role.positions[0] === group))
                .map((group) => (
                  <optgroup label={`${positionNames[group]}s`} key={group}>
                    {availableRoles
                      .filter((role) => role.positions[0] === group)
                      .map((role) => (
                        <option value={role.role_id} key={role.role_id}>
                          {role.name}
                          {role.feature_set_version !== "event_intelligence_v1"
                            ? " (older version)"
                            : ""}
                        </option>
                      ))}
                  </optgroup>
                ))}
            </select>
            <small className="field-hint">
              {activeRole
                ? `Prioritises ${rolePriorities(activeRole).join(", ")}.`
                : playerPosition
                  ? `Showing ${positionNames[playerPosition]?.toLowerCase() ?? ""} roles.`
                  : "Pick a player first to see roles for their position."}
            </small>
          </label>
          <label>
            Max value (€m, optional)
            <input
              inputMode="decimal"
              value={maxValue}
              onChange={(e) => setMaxValue(e.target.value.replace(/[^0-9.]/g, ""))}
              placeholder="e.g. 20"
            />
            <small className="field-hint">Value at the time of that season.</small>
          </label>
          <button disabled={!player || loading} onClick={run}>
            {loading ? "Comparing…" : "Find similar players"}
          </button>
        </div>
        {loading ? <PageLoader label="Finding similar players…" /> : null}
        {error && <div className="notice">{error}</div>}
        {!result ? (
          <EmptyState
            title={
              player
                ? `${player.canonical_name} is ready to compare`
                : "Select a reference player"
            }
            icon="↔"
          >
            {player
              ? "Press “Find similar players” to see who plays most like them."
              : "Start by searching for a player whose style you want more of."}
          </EmptyState>
        ) : (
          <>
            <div className="card-top">
              <div>
                <div className="eyebrow">Compare and decide</div>
                <h2>Players most like {player?.canonical_name}</h2>
                <p className="analysis-copy">
                  {activeRole
                    ? `Ranked by overall match: 60% style match with ${player?.canonical_name ?? "the reference player"}, 40% fit for the ${activeRole.name.toLowerCase()} role.`
                    : `Ranked by style match: how closely each player's numbers line up with ${player?.canonical_name ?? "the reference player"}'s. Choose a role to also rank by role fit.`}
                </p>
              </div>
              <label className="inline-filter">
                Add to shortlist
                <select
                  value={selectedList}
                  onChange={(e) => setSelectedList(e.target.value)}
                >
                  <option value="">Choose active list</option>
                  {lists.map((list) => (
                    <option value={list.shortlist_id} key={list.shortlist_id}>
                      {list.name} · {list.player_count} players
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {selectedRole &&
            result.data.length > 0 &&
            result.data[0].role_weighted_feature_count === 0 ? (
              <div className="notice">
                This saved role uses the retired basic-stat feature set, so its
                preferences could not weight the advanced model. Recreate it
                below to apply role-specific priorities.
              </div>
            ) : null}
            {limit !== null ? (
              <div className="notice">
                {hiddenByValue} of {allCandidates.length} candidates hidden: they were valued above
                €{maxValue}m or have no linked market value. Values are a historical snapshot taken
                at the end of each candidate's own season.
              </div>
            ) : null}
            <div className="similar-list">
              {visibleCandidates.map((candidate, index) => {
                const diffs = Object.entries(
                  candidate.feature_differences ?? {},
                ).sort(
                  (a, b) =>
                    Math.abs(a[1].difference) - Math.abs(b[1].difference),
                );
                const closest = diffs[0],
                  tradeoff = [...diffs].sort(
                    (a, b) =>
                      Math.abs(b[1].difference) - Math.abs(a[1].difference),
                  )[0];
                return (
                  <article className="similar-card" key={candidate.player_id}>
                    <span className="avatar">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <h3>
                        <a href={`/players/${candidate.player_id}`}>
                          {candidate.name}
                        </a>
                      </h3>
                      <p>
                        {candidate.team_name || "Club unavailable"} ·{" "}
                        {positionNames[candidate.position_group ?? ""] ||
                          "Position unavailable"}{" "}
                        · {formatNumber(candidate.minutes_played, 0)} min ·{" "}
                        {candidate.market_value_eur
                          ? `valued ${euros(candidate.market_value_eur)} then · `
                          : ""}
                        {formatNumber(candidate.compared_feature_count, 0)}/
                        {formatNumber(candidate.target_feature_count, 0)}{" "}
                        features · {candidate.confidence ?? "Unknown"}{" "}
                        confidence
                      </p>
                      <p>
                        {closest
                          ? `Closest evidence: ${humanize(closest[0]).toLowerCase()} (${Math.abs(closest[1].difference).toFixed(1)} percentile points). `
                          : ""}
                        {tradeoff
                          ? `Largest difference: ${humanize(tradeoff[0]).toLowerCase()} (${Math.abs(tradeoff[1].difference).toFixed(1)} points).`
                          : "Full feature coverage unavailable."}
                      </p>
                    </div>
                    <div>
                      <div className="score">
                        {formatNumber(
                          selectedRole
                            ? candidate.recommendation_score
                            : candidate.similarity_score,
                          0,
                        )}
                        <small>
                          {selectedRole
                            ? "overall match / 100"
                            : "style match / 100"}
                        </small>
                        {selectedRole && candidate.role_fit_score != null ? (
                          <small>
                            {formatNumber(candidate.similarity_score, 0)}{" "}
                            style
                            {" · "}
                            {formatNumber(candidate.role_fit_score, 0)} role fit
                          </small>
                        ) : null}
                      </div>
                      <button
                        className="secondary"
                        onClick={() => void addCandidate(candidate, index + 1)}
                      >
                        Shortlist
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
            {!result.data.length && (
              <EmptyState title="Not enough comparable evidence">
                No peers meet the same-league, same-position and advanced-event
                overlap threshold. This is a coverage gap, not a zero score.
              </EmptyState>
            )}
            <Methodology meta={result.meta} />
          </>
        )}
        {message && <div className="notice">{message}</div>}
      </section>
      <section className="panel">
        <details className="role-builder">
          <summary className="card-top">
            <div>
              <div className="eyebrow">Optional</div>
              <h2>Make your own role</h2>
              <p className="analysis-copy">
                None of the built-in roles fit? Choose what matters and save it for future searches.
              </p>
            </div>
            <span className="tag">Create a role +</span>
          </summary>
          <form className="workflow" onSubmit={saveRole}>
            <label>
              Role name
              <input
                required
                value={roleName}
                onChange={(e) => setRoleName(e.target.value)}
                placeholder="e.g. Progressive right winger"
              />
            </label>
            <label>
              Position
              <select
                value={position}
                onChange={(e) => {
                  const next = e.target.value;
                  setPosition(next);
                  setWeights(rolePreset("Balanced profile", next));
                }}
              >
                {Object.entries(positionNames).map(([value, label]) => (
                  <option value={value} key={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Minimum evidence
              <select
                value={minimumMinutes}
                onChange={(e) => setMinimumMinutes(e.target.value)}
              >
                <option value="900">900+ minutes</option>
                <option value="1800">1,800+ minutes</option>
              </select>
            </label>
            <label>
              Maximum age (optional)
              <input
                type="number"
                min="15"
                max="45"
                value={maximumAge}
                onChange={(e) => setMaximumAge(e.target.value)}
                placeholder="No age limit"
              />
            </label>
            <label>
              Preference template
              <select
                onChange={(e) =>
                  setWeights(rolePreset(e.target.value, position))
                }
              >
                <option>Balanced profile</option>
                {position === "GK" ? (
                  <>
                    <option>Shot prevention</option>
                    <option>Area control</option>
                    <option>Sweeper keeper</option>
                  </>
                ) : (
                  <>
                    <option>Progressive creator</option>
                    <option>Ball-carrying threat</option>
                    <option>Defensive reader</option>
                  </>
                )}
              </select>
            </label>
            <button>Save role</button>
          </form>
          <div className="percentile-list role-weights">
            {roleMetrics.map((metric) => (
              <label className="field" key={metric}>
                {humanize(metric).replace("Per 90", "")} importance:{" "}
                <strong>{weights[metric] ? `${weights[metric]}/5` : "Not used"}</strong>
                <input
                  aria-label={`${humanize(metric)} importance`}
                  type="range"
                  min="0"
                  max="5"
                  value={weights[metric]}
                  onChange={(e) =>
                    setWeights({ ...weights, [metric]: Number(e.target.value) })
                  }
                />
              </label>
            ))}
          </div>
          <p className="analysis-copy">
            <strong>Minimum minutes and age</strong> rule players out completely.{" "}
            <strong>The sliders</strong> set how much each stat counts towards role fit; set one
            to 0 to ignore it. Style match is always worked out separately.
          </p>
        </details>
      </section>
      <section className="panel">
        <details className="role-builder">
          <summary className="card-top">
            <div>
              <div className="eyebrow">Reference</div>
              <h2>All {roles.length} roles and what they prioritise</h2>
            </div>
            <span className="tag">Show roles +</span>
          </summary>
          {roles.length ? (
            positionOrder.map((group) => {
              const groupRoles = roles.filter((role) => role.positions[0] === group);
              if (!groupRoles.length) return null;
              return (
                <div key={group} className="role-group">
                  <h3>{positionNames[group]}s</h3>
                  <div className="source-cards">
                    {groupRoles.map((role) => (
                      <article className="source-card" key={role.role_id}>
                        <strong>{role.name}</strong>
                        <p>Prioritises {rolePriorities(role).join(", ")}.</p>
                        <small>
                          {String(role.hard_constraints?.minimum_minutes ?? 900)}+ minutes
                          {role.hard_constraints?.maximum_age
                            ? ` · age ${String(role.hard_constraints.maximum_age)} or under`
                            : ""}
                        </small>
                      </article>
                    ))}
                  </div>
                </div>
              );
            })
          ) : (
            <EmptyState title="No roles yet">
              Create a role above to keep the brief attached to later decisions.
            </EmptyState>
          )}
          <a className="text-link" href="/shortlists">
            Open your shortlists →
          </a>
        </details>
      </section>
    </main>
  );
}
