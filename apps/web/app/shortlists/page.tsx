"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ShortlistPlan } from "../shortlist-plan";
import { API, EmptyState, Player, PlayerSearch } from "../components";
import { StatusMessage } from "../page-loader";

type Role = { role_id: number; name: string; positions: string[] };
type CandidateIntelligence = {
  status: string;
  archetype?: string;
  role_fit_score?: number | null;
  role_feature_coverage: number;
  role_feature_total: number;
  strongest_signal?: string | null;
  main_question?: string | null;
  context?: {
    team_name?: string;
    competition_name?: string;
    season_label?: string;
    position_group?: string;
    minutes_played?: number;
  };
  data_as_of?: string;
};
type DecisionEvidence = {
  model_version: string;
  reference_player_id: number;
  reference_player_name: string;
  similarity_score: number;
  role_fit_score: number | null;
  recommendation_score: number;
  feature_coverage_pct: number;
  compared_feature_count: number;
  target_feature_count: number;
  closest_metric?: string | null;
  largest_difference_metric?: string | null;
  competition_name?: string | null;
  season_label?: string | null;
  position_group?: string | null;
};
type Candidate = {
  player_id: number;
  name: string;
  rank: number | null;
  stage: string;
  rationale: string | null;
  added_at: string;
  intelligence?: CandidateIntelligence;
  decision_evidence?: DecisionEvidence | null;
};
type Shortlist = {
  shortlist_id: number;
  name: string;
  role_id?: number | null;
  role_name?: string;
  role_positions?: string[];
  role_feature_weights?: Record<string, number>;
  role_feature_set_version?: string;
  status: string;
  player_count: number;
  players?: Candidate[];
};
const stages = ["IDENTIFIED", "REVIEWING", "CONTACTED", "REJECTED"];
const stageNames: Record<string, string> = {
  IDENTIFIED: "Identified",
  REVIEWING: "Under review",
  CONTACTED: "Contacted",
  REJECTED: "Not progressing",
};

export default function ShortlistsPage() {
  const [roles, setRoles] = useState<Role[]>([]),
    [lists, setLists] = useState<Shortlist[]>([]),
    [selected, setSelected] = useState<Shortlist | null>(null),
    [name, setName] = useState(""),
    [roleId, setRoleId] = useState(""),
    [message, setMessage] = useState("Loading recruitment workspace…"),
    [candidate, setCandidate] = useState<Player | null>(null),
    [rank, setRank] = useState(""),
    [stage, setStage] = useState("IDENTIFIED"),
    [rationale, setRationale] = useState(""),
    [view, setView] = useState<"lists" | "plan">("lists");
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("view") === "plan") setView("plan");
  }, []);
  // Removal waits a few seconds so "Undo" can restore the candidate with its notes intact.
  const [removing, setRemoving] = useState<{ shortlistId: number; item: Candidate } | null>(null);
  const pendingRemoval = useRef<{ shortlistId: number; item: Candidate; timer: number } | null>(null);
  function commitRemoval(keepalive = false) {
    const pending = pendingRemoval.current;
    if (!pending) return;
    window.clearTimeout(pending.timer);
    pendingRemoval.current = null;
    setRemoving(null);
    void fetch(`${API}/shortlists/${pending.shortlistId}/players/${pending.item.player_id}`, {
      method: "DELETE",
      keepalive,
    })
      .then((response) => {
        if (!response.ok && response.status !== 404) throw new Error(String(response.status));
        if (!keepalive) void load();
      })
      .catch(() => setMessage(`Could not remove ${pending.item.name}. Refresh and try again.`));
  }
  function removeCandidate(item: Candidate) {
    if (!selected) return;
    commitRemoval();
    const shortlistId = selected.shortlist_id;
    const timer = window.setTimeout(() => commitRemoval(), 6000);
    pendingRemoval.current = { shortlistId, item, timer };
    setRemoving({ shortlistId, item });
  }
  function undoRemoval() {
    const pending = pendingRemoval.current;
    if (pending) window.clearTimeout(pending.timer);
    pendingRemoval.current = null;
    setRemoving(null);
  }
  useEffect(() => {
    const flush = () => commitRemoval(true);
    window.addEventListener("pagehide", flush);
    return () => {
      window.removeEventListener("pagehide", flush);
      flush();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  function switchView(next: "lists" | "plan") {
    setView(next);
    window.history.replaceState(null, "", next === "plan" ? "/shortlists?view=plan" : "/shortlists");
  }
  async function load() {
    try {
      const [rr, sr] = await Promise.all([
        fetch(`${API}/recruitment/roles`),
        fetch(`${API}/shortlists`),
      ]);
      if (!rr.ok || !sr.ok) throw Error("API request failed");
      const [rp, sp] = await Promise.all([rr.json(), sr.json()]);
      setRoles(rp.data ?? []);
      setLists(sp.data ?? []);
      setMessage("");
      if (selected) {
        const refreshed = await fetch(
          `${API}/shortlists/${selected.shortlist_id}`,
        );
        if (refreshed.ok) setSelected((await refreshed.json()).data);
      }
    } catch (e) {
      setMessage(
        `Recruitment workspace unavailable: ${e instanceof Error ? e.message : "unknown error"}`,
      );
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function create(event: FormEvent) {
    event.preventDefault();
    const response = await fetch(`${API}/shortlists`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, role_id: roleId ? Number(roleId) : null }),
    });
    if (!response.ok) {
      setMessage(`Could not create shortlist: API returned ${response.status}`);
      return;
    }
    const payload = await response.json();
    setName("");
    setRoleId("");
    setMessage(
      "Shortlist created. Add candidates and record the decision rationale below.",
    );
    await load();
    await open(payload.data.shortlist_id);
  }
  async function open(id: number) {
    const response = await fetch(`${API}/shortlists/${id}`);
    if (!response.ok) {
      setMessage("Could not open this shortlist.");
      return;
    }
    setSelected((await response.json()).data);
    setCandidate(null);
    setRank("");
    setRationale("");
  }
  async function saveCandidate(event: FormEvent) {
    event.preventDefault();
    if (!selected || !candidate) return;
    const response = await fetch(
      `${API}/shortlists/${selected.shortlist_id}/players`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_id: candidate.player_id,
          rank: rank ? Number(rank) : null,
          stage,
          rationale: rationale || null,
        }),
      },
    );
    setMessage(
      response.ok
        ? `${candidate.canonical_name} saved to ${selected.name}.`
        : `Could not save candidate: API returned ${response.status}`,
    );
    if (response.ok) {
      setCandidate(null);
      setRank("");
      setRationale("");
      await load();
    }
  }
  async function updateCandidate(item: Candidate, nextStage = item.stage) {
    if (!selected) return;
    const response = await fetch(
      `${API}/shortlists/${selected.shortlist_id}/players`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_id: item.player_id,
        rank: item.rank,
        stage: nextStage,
        rationale: item.rationale,
      }),
      },
    );
    setMessage(
      response.ok
        ? `${item.name} moved to ${stageNames[nextStage].toLowerCase()}.`
        : "Could not update the workflow stage.",
    );
    if (response.ok) await load();
  }
  async function archive() {
    if (!selected) return;
    const response = await fetch(
      `${API}/shortlists/${selected.shortlist_id}/archive`,
      { method: "POST" },
    );
    setMessage(
      response.ok
        ? `${selected.name} archived. Its decision trail remains available.`
        : "Could not archive this shortlist.",
    );
    if (response.ok) {
      setSelected(null);
      await load();
    }
  }
  const active = lists.filter((item) => item.status === "ACTIVE"),
    archived = lists.filter((item) => item.status === "ARCHIVED");
  return (
    <main className="product-page" id="workspace-content">
      <div className="page-head">
        <div>
          <div className="eyebrow">Recruitment workspace</div>
          <h1 className="page-title">Your shortlists</h1>
          <p className="lede">
            Keep ranking, workflow stage and football rationale attached to
            every candidate from first review to final decision.
          </p>
        </div>
        <span className="tag">
          {active.length} active list{active.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="view-tabs" role="tablist" aria-label="Shortlist views">
        <button role="tab" aria-selected={view === "lists"} className={view === "lists" ? "active" : ""} onClick={() => switchView("lists")}>
          Shortlists
        </button>
        <button role="tab" aria-selected={view === "plan"} className={view === "plan" ? "active" : ""} onClick={() => switchView("plan")}>
          Coverage &amp; budget
        </button>
      </div>
      {view === "plan" ? (
        <ShortlistPlan />
      ) : (
      <>
      <section className="panel">
        <div className="card-top">
          <div>
            <div className="eyebrow">Create a decision workspace</div>
            <h2>New shortlist</h2>
          </div>
          <a className="text-link" href="/recruitment">
            Define recruitment roles →
          </a>
        </div>
        <form className="workflow" onSubmit={create}>
          <label>
            Shortlist name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Summer left-back options"
            />
          </label>
          <label>
            Recruitment role
            <select value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              <option value="">No role assigned</option>
              {roles.map((role) => (
                <option key={role.role_id} value={role.role_id}>
                  {role.name} · {role.positions.join("/")}
                </option>
              ))}
            </select>
          </label>
          <button>Create shortlist</button>
        </form>
        <StatusMessage message={message} />
      </section>
      <div className="two-col shortlist-layout">
        <section className="panel">
          <div className="card-top">
            <h2>Active shortlists</h2>
            <span className="tag">{active.length}</span>
          </div>
          <div className="player-list">
            {active.map((item) => (
              <button
                className="card shortlist-button"
                aria-pressed={selected?.shortlist_id === item.shortlist_id}
                key={item.shortlist_id}
                onClick={() => void open(item.shortlist_id)}
              >
                <div className="card-top">
                  <span className="tag">{item.role_name || "Open brief"}</span>
                  <span className="badge">
                    {item.player_count} player
                    {item.player_count === 1 ? "" : "s"}
                  </span>
                </div>
                <h3>{item.name}</h3>
                <p>Open decision trail →</p>
              </button>
            ))}
          </div>
          {!active.length && (
            <EmptyState title="No active shortlists">
              Create a shortlist above or archive completed decision workspaces.
            </EmptyState>
          )}
          <details className="methodology">
            <summary>Archived shortlists ({archived.length})</summary>
            <div className="player-list">
              {archived.map((item) => (
                <button
                  className="card shortlist-button"
                  aria-pressed={selected?.shortlist_id === item.shortlist_id}
                  key={item.shortlist_id}
                  onClick={() => void open(item.shortlist_id)}
                >
                  <strong>{item.name}</strong>
                  <p>
                    {item.player_count} retained candidate
                    {item.player_count === 1 ? "" : "s"} · archived
                  </p>
                </button>
              ))}
            </div>
          </details>
        </section>
        <section className="panel">
          <div className="card-top">
            <div>
              <div className="eyebrow">Decision trail</div>
              <h2>{selected?.name || "Choose a shortlist"}</h2>
            </div>
            {selected?.status === "ACTIVE" && (
              <button className="secondary" onClick={() => void archive()}>
                Archive list
              </button>
            )}
          </div>
          {!selected ? (
            <EmptyState title="Open a shortlist">
              Select an active or archived list to view its candidates,
              rankings, stages and rationale.
            </EmptyState>
          ) : (
            <>
              <div className="shortlist-brief">
                <div>
                  <strong>
                    {selected.role_name || "Open recruitment brief"}
                  </strong>
                  <small>
                    {selected.role_positions?.join(" / ") ||
                      "No position constraint"}{" "}
                    ·{" "}
                    {selected.status === "ACTIVE"
                      ? "Active decision"
                      : "Archived record"}
                  </small>
                </div>
                <div>
                  <strong>
                    {Object.keys(selected.role_feature_weights ?? {}).length}
                  </strong>
                  <small>weighted evidence features</small>
                </div>
                <div>
                  <strong>
                    {selected.role_feature_set_version || "Manual"}
                  </strong>
                  <small>feature model</small>
                </div>
              </div>
              {selected.status === "ACTIVE" && (
                <form onSubmit={saveCandidate}>
                  <PlayerSearch onSelect={setCandidate} label="Add a player" />
                  <div className="workflow">
                    <label>
                      Rank
                      <input
                        type="number"
                        min="1"
                        value={rank}
                        onChange={(e) => setRank(e.target.value)}
                        placeholder="Optional"
                      />
                    </label>
                    <label>
                      Workflow stage
                      <select
                        value={stage}
                        onChange={(e) => setStage(e.target.value)}
                      >
                        {stages.map((item) => (
                          <option value={item} key={item}>
                            {stageNames[item]}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <label className="field">
                    Scouting rationale
                    <textarea
                      maxLength={2000}
                      value={rationale}
                      onChange={(e) => setRationale(e.target.value)}
                      placeholder="Why this player belongs on the list; include evidence and the main uncertainty."
                    />
                  </label>
                  <button className="action" disabled={!candidate}>
                    Save candidate
                  </button>
                </form>
              )}
              {removing && removing.shortlistId === selected.shortlist_id ? (
                <div className="undo-bar" role="status">
                  <span>
                    Removed <strong>{removing.item.name}</strong> from this shortlist.
                  </span>
                  <button type="button" onClick={undoRemoval}>
                    Undo
                  </button>
                </div>
              ) : null}
              <div className="shortlist-evidence-list">
                {(selected.players ?? [])
                  .filter(
                    (item) =>
                      !(
                        removing &&
                        removing.shortlistId === selected.shortlist_id &&
                        removing.item.player_id === item.player_id
                      ),
                  )
                  .map((item) => (
                  <article
                    className="shortlist-evidence-card"
                    key={item.player_id}
                  >
                    <div className="candidate-heading">
                      <span className="avatar">{item.rank ?? "—"}</span>
                      <div>
                        <h3>
                          <a href={`/players/${item.player_id}`}>{item.name}</a>
                        </h3>
                        <small>
                          {item.intelligence?.context
                            ? [
                                item.intelligence.context.team_name,
                                item.intelligence.context.competition_name,
                                item.intelligence.context.season_label,
                              ]
                                .filter(Boolean)
                                .join(" · ")
                            : "No comparable event context"}
                        </small>
                      </div>
                      <div>
                        {selected.status === "ACTIVE" ? (
                          <select
                            aria-label={`Workflow stage for ${item.name}`}
                            value={item.stage}
                            onChange={(e) =>
                              void updateCandidate(item, e.target.value)
                            }
                          >
                            {stages.map((value) => (
                              <option value={value} key={value}>
                                {stageNames[value]}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="tag">
                            {stageNames[item.stage] ?? item.stage}
                          </span>
                        )}
                        {selected.status === "ACTIVE" ? (
                          <button
                            type="button"
                            className="remove-candidate"
                            aria-label={`Remove ${item.name} from this shortlist`}
                            title="Remove from shortlist"
                            onClick={() => removeCandidate(item)}
                          >
                            ×
                          </button>
                        ) : null}
                      </div>
                    </div>
                    {item.decision_evidence ? (
                      <div className="decision-snapshot">
                        <div>
                          <strong>
                            {Math.round(item.decision_evidence.recommendation_score)}/100
                          </strong>
                          <small>captured recommendation</small>
                        </div>
                        <div>
                          <strong>
                            {Math.round(item.decision_evidence.similarity_score)}/100
                          </strong>
                          <small>style similarity</small>
                        </div>
                        <div>
                          <strong>
                            {item.decision_evidence.role_fit_score == null
                              ? "—"
                              : `${Math.round(item.decision_evidence.role_fit_score)}/100`}
                          </strong>
                          <small>role fit at selection</small>
                        </div>
                        <p>
                          Compared with {item.decision_evidence.reference_player_name} ·{" "}
                          {item.decision_evidence.competition_name ||
                            "competition unavailable"}{" "}
                          · {item.decision_evidence.season_label || "season unavailable"} ·{" "}
                          {Math.round(item.decision_evidence.feature_coverage_pct)}% feature
                          coverage
                        </p>
                      </div>
                    ) : null}
                    {item.intelligence?.status === "AVAILABLE" ? (
                      <>
                        <div className="candidate-intelligence">
                          <div>
                            <strong>{item.intelligence.archetype}</strong>
                            <small>evidence-led archetype</small>
                          </div>
                          <div>
                            <strong>
                              {item.intelligence.role_fit_score == null
                                ? "—"
                                : `${Math.round(item.intelligence.role_fit_score)}/100`}
                            </strong>
                            <small>role fit</small>
                          </div>
                          <div>
                            <strong>
                              {item.intelligence.role_feature_coverage}/
                              {item.intelligence.role_feature_total}
                            </strong>
                            <small>role features observed</small>
                          </div>
                          <div>
                            <strong>
                              {item.intelligence.context?.minutes_played?.toLocaleString() ??
                                "—"}
                            </strong>
                            <small>context minutes</small>
                          </div>
                        </div>
                        <div className="evidence-callouts">
                          <p>
                            <strong>Strongest signal:</strong>{" "}
                            {item.intelligence.strongest_signal ||
                              "No metric clears the high-evidence threshold."}
                          </p>
                          <p>
                            <strong>Main question:</strong>{" "}
                            {item.intelligence.main_question ||
                              "No metric falls below the low-evidence threshold."}
                          </p>
                        </div>
                      </>
                    ) : (
                      <div className="notice">
                        Advanced event evidence is unavailable for this
                        candidate; do not infer role fit from missing data.
                      </div>
                    )}
                    <blockquote>
                      {item.rationale ||
                        "Rationale not recorded—review required."}
                    </blockquote>
                    <small>
                      Added {new Date(item.added_at).toLocaleDateString()} ·
                      statistical evidence supports review, not a final verdict
                    </small>
                  </article>
                ))}
              </div>
              {!(selected.players ?? []).length && (
                <EmptyState title="No candidates yet">
                  Add a player above or send a ranked alternative here from
                  Recruitment Search.
                </EmptyState>
              )}
            </>
          )}
        </section>
      </div>
      </>
      )}
    </main>
  );
}
