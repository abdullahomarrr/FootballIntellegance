"use client";

import { useEffect, useMemo, useState } from "react";
import { API, EmptyState, Envelope, Methodology, Stat } from "./components";
import { euros } from "./market-panel";
import { PageLoader } from "./page-loader";

type Candidate = {
  player_id: number;
  name: string;
  rank: number | null;
  stage: string;
  rationale: string | null;
  added_at: string;
  market_value_eur?: number | null;
  season_label?: string | null;
  decision_evidence?: {
    reference_player_name: string;
    similarity_score: number;
    role_fit_score?: number | null;
    recommendation_score: number;
    feature_coverage_pct: number;
    competition_name?: string | null;
    season_label?: string | null;
  } | null;
  intelligence?: {
    status: string;
    archetype?: string;
    role_fit_score?: number | null;
    role_feature_coverage: number;
    role_feature_total: number;
    strongest_signal?: string | null;
    main_question?: string | null;
  };
};
type Shortlist = {
  shortlist_id: number;
  name: string;
  role_name?: string | null;
  role_positions?: string[] | null;
  role_feature_set_version?: string | null;
  status: string;
  players?: Candidate[];
};
type PlanningCandidate = Candidate & {
  shortlist_id: number;
  shortlist_name: string;
  role_name: string;
  positions: string[];
};

const positions = [
  ["GK", "Goalkeeper"],
  ["DF", "Defence"],
  ["MD", "Midfield"],
  ["FW", "Attack"],
] as const;
const stageLabels: Record<string, string> = {
  IDENTIFIED: "Identified",
  REVIEWING: "Under review",
  CONTACTED: "Contacted",
  REJECTED: "Not progressing",
};
const stagePriority: Record<string, number> = {
  CONTACTED: 0,
  REVIEWING: 1,
  IDENTIFIED: 2,
  REJECTED: 3,
};

/** Coverage and budget view across the active shortlists (shown as a tab on Shortlists). */
export function ShortlistPlan() {
  const [lists, setLists] = useState<Shortlist[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/shortlists`)
      .then(async (response) => {
        if (!response.ok) throw new Error(String(response.status));
        const payload: Envelope<Shortlist[]> = await response.json();
        const active = payload.data.filter((list) => list.status === "ACTIVE");
        return Promise.all(
          active.map(async (list) => {
            const detail = await fetch(
              `${API}/shortlists/${list.shortlist_id}`,
            );
            return detail.ok ? ((await detail.json()).data as Shortlist) : list;
          }),
        );
      })
      .then(setLists)
      .catch(() =>
        setError(
          "Squad evidence could not be loaded from the recruitment workspace.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  const candidates = useMemo(
    () =>
      lists
        .flatMap((list) =>
          (list.players ?? []).map((candidate) => ({
            ...candidate,
            shortlist_id: list.shortlist_id,
            shortlist_name: list.name,
            role_name: list.role_name ?? "Open recruitment brief",
            positions: list.role_positions ?? [],
          })),
        )
        .sort(
          (left, right) =>
            (stagePriority[left.stage] ?? 9) -
              (stagePriority[right.stage] ?? 9) ||
            (left.rank ?? 999) - (right.rank ?? 999),
        ),
    [lists],
  );
  const progressing = candidates.filter(
    (candidate) => candidate.stage !== "REJECTED",
  );
  const coveredPositions = positions.filter(([code]) =>
    progressing.some((candidate) => candidate.positions.includes(code)),
  ).length;
  const activeDecisions = progressing.filter((candidate) =>
    ["REVIEWING", "CONTACTED"].includes(candidate.stage),
  ).length;

  return (
    <div className="shortlist-plan">
      {error ? <div className="notice">{error}</div> : null}
      {loading ? <PageLoader label="Building squad coverage…" /> : null}
      <section className="stat-grid">
        <Stat label="Active briefs" value={lists.length} />
        <Stat label="Candidates" value={progressing.length} />
        <Stat label="In review / contacted" value={activeDecisions} />
        <Stat label="Position groups covered" value={`${coveredPositions}/4`} />
      </section>
      <BudgetPlanner candidates={progressing} />
      <section className="panel">
        <div className="section-title">
          <div>
            <div className="eyebrow">Coverage map</div>
            <h2>Where the pipeline is strong—and empty</h2>
          </div>
        </div>
        <div className="squad-coverage-grid">
          {positions.map(([code, label]) => {
            const options = progressing.filter((candidate) =>
              candidate.positions.includes(code),
            );
            return (
              <article
                className={
                  options.length ? "coverage-role" : "coverage-role gap"
                }
                key={code}
              >
                <div className="card-top">
                  <span>{code}</span>
                  <span className={options.length ? "tag" : "tag warn"}>
                    {options.length
                      ? `${options.length} option${options.length === 1 ? "" : "s"}`
                      : "Gap"}
                  </span>
                </div>
                <h3>{label}</h3>
                {options.slice(0, 3).map((candidate) => (
                  <a
                    href={`/players/${candidate.player_id}`}
                    key={`${candidate.shortlist_id}-${candidate.player_id}`}
                  >
                    <strong>{candidate.name}</strong>
                    <small>
                      {stageLabels[candidate.stage] ?? candidate.stage} ·{" "}
                      {candidate.role_name}
                      {(candidate.decision_evidence?.role_fit_score ??
                        candidate.intelligence?.role_fit_score) != null
                        ? ` · ${Math.round(candidate.decision_evidence?.role_fit_score ?? candidate.intelligence!.role_fit_score!)}/100 fit`
                        : " · fit unverified"}
                    </small>
                  </a>
                ))}
                {!options.length ? (
                  <p>No active role-backed candidate covers this group.</p>
                ) : null}
              </article>
            );
          })}
        </div>
      </section>
      <section className="panel">
        <div className="section-title">
          <div>
            <div className="eyebrow">Decision pipeline</div>
            <h2>Evidence carried forward from recruitment</h2>
          </div>
          <a className="text-link" href="/recruitment">
            Find alternatives →
          </a>
        </div>
        {progressing.length ? (
          <div className="squad-pipeline">
            {progressing.map((candidate) => (
              <article key={`${candidate.shortlist_id}-${candidate.player_id}`}>
                <span className="avatar">{candidate.rank ?? "—"}</span>
                <div>
                  <h3>
                    <a href={`/players/${candidate.player_id}`}>
                      {candidate.name}
                    </a>
                  </h3>
                  <p>
                    {candidate.role_name} ·{" "}
                    {candidate.positions.join(" / ") || "Position not attached"}{" "}
                    · {stageLabels[candidate.stage] ?? candidate.stage}
                  </p>
                  {candidate.intelligence?.status === "AVAILABLE" ? (
                    <div className="pipeline-evidence">
                      {candidate.decision_evidence ? (
                        <span>
                          {Math.round(candidate.decision_evidence.recommendation_score)}/100
                          captured recommendation
                        </span>
                      ) : null}
                      <span>
                        {candidate.intelligence.archetype ??
                          "Archetype not classified"}
                      </span>
                      <span>
                        {candidate.intelligence.role_fit_score == null
                          ? "Role fit unavailable"
                          : `${Math.round(candidate.intelligence.role_fit_score)}/100 role fit`}
                      </span>
                      <span>
                        {candidate.intelligence.role_feature_coverage}/
                        {candidate.intelligence.role_feature_total} features
                      </span>
                    </div>
                  ) : (
                    <div className="pipeline-evidence missing">
                      Advanced event fit unavailable
                    </div>
                  )}
                  <blockquote>
                    {candidate.rationale ??
                      "No evidence rationale recorded—review before progressing."}
                  </blockquote>
                  {candidate.intelligence?.main_question ? (
                    <small className="pipeline-question">
                      Review question: {candidate.intelligence.main_question}
                    </small>
                  ) : null}
                </div>
                <span className="tag">{candidate.shortlist_name}</span>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No active squad options">
            Add candidates through Recruitment Search and attach them to a
            role-backed shortlist to populate this plan.
          </EmptyState>
        )}
      </section>
      <section className="panel planning-limitations">
        <div>
          <div className="eyebrow">Deliberate limits</div>
          <h2>What this plan does not pretend to know</h2>
        </div>
        <div className="source-cards">
          <article className="source-card">
            <strong>Transfer costs &amp; wages</strong>
            <p>
              The budget view uses dated market-value estimates, not fees.
              Wages and agent costs are not covered.
            </p>
          </article>
          <article className="source-card">
            <strong>Medical availability</strong>
            <p>
              Injury and fitness status require a current, permitted source and
              remain a manual scout check.
            </p>
          </article>
          <article className="source-card">
            <strong>Final selection</strong>
            <p>
              Statistical fit narrows review; video, live observation and human
              judgment still make the decision.
            </p>
          </article>
        </div>
        <Methodology
          meta={{
            model_version: "shortlist_squad_coverage_v1",
            active_shortlists: lists.length,
            candidate_sample: progressing.length,
            cost_model_status: "UNAVAILABLE_WITHOUT_LICENSED_DATA",
          }}
        />
      </section>
    </div>
  );
}


function stored(key: string) {
  try {
    return window.localStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}
function remember(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage can be unavailable; the planner still works for this visit */
  }
}

function BudgetPlanner({ candidates }: { candidates: PlanningCandidate[] }) {
  const [budget, setBudget] = useState("");
  const [prices, setPrices] = useState<Record<string, string>>({});
  useEffect(() => {
    setBudget(stored("squad-budget-m"));
    try {
      setPrices(JSON.parse(stored("squad-prices") || "{}") as Record<string, string>);
    } catch {
      setPrices({});
    }
  }, []);
  const people = useMemo(() => {
    const seen = new Map<number, PlanningCandidate>();
    for (const candidate of candidates) if (!seen.has(candidate.player_id)) seen.set(candidate.player_id, candidate);
    return [...seen.values()];
  }, [candidates]);
  const cost = (candidate: PlanningCandidate) => {
    const manual = Number(prices[String(candidate.player_id)]);
    if (prices[String(candidate.player_id)] && Number.isFinite(manual)) return manual * 1_000_000;
    return candidate.market_value_eur ?? null;
  };
  const known = people.filter((candidate) => cost(candidate) !== null);
  const total = known.reduce((sum, candidate) => sum + (cost(candidate) ?? 0), 0);
  const limit = budget ? Number(budget) * 1_000_000 : null;
  const unknown = people.length - known.length;
  return (
    <section className="panel budget-panel">
      <div className="section-title">
        <div>
          <div className="eyebrow">Budget view</div>
          <h2>What the shortlist would cost, on the numbers you trust</h2>
        </div>
        <span className="tag">Your inputs + historical snapshot</span>
      </div>
      <p className="analysis-copy">
        Costs default to each candidate's historical market value (a crowd-sourced estimate at the
        end of the season you shortlisted them from, not a transfer fee). Type your own price to
        override it. Wages are not estimated: there is no free, reliable source.
      </p>
      <label className="budget-input">
        Transfer budget (€m)
        <input
          inputMode="decimal"
          value={budget}
          placeholder="e.g. 80"
          onChange={(event) => {
            const value = event.target.value.replace(/[^0-9.]/g, "");
            setBudget(value);
            remember("squad-budget-m", value);
          }}
        />
      </label>
      {people.length ? (
        <>
          <div className="stat-grid budget-stats">
            <Stat label="Shortlist cost" value={euros(total)} detail={`${known.length} priced of ${people.length}`} />
            <Stat
              label={limit !== null && total > limit ? "Over budget by" : "Budget remaining"}
              value={limit !== null ? euros(Math.abs(limit - total)) : "—"}
              detail={limit !== null ? `of ${euros(limit)}` : "enter a budget"}
            />
            <Stat label="Unpriced candidates" value={unknown} detail="not counted in the total" />
          </div>
          <div className="table-wrap">
            <table className="transfer-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Role</th>
                  <th>Snapshot value</th>
                  <th>Your price (€m)</th>
                </tr>
              </thead>
              <tbody>
                {people.map((candidate) => (
                  <tr key={candidate.player_id}>
                    <td>
                      <a className="text-link" href={`/players/${candidate.player_id}`}>
                        {candidate.name}
                      </a>
                    </td>
                    <td>{candidate.role_name}</td>
                    <td>
                      {candidate.market_value_eur
                        ? `${euros(candidate.market_value_eur)} (${candidate.season_label ?? "season"})`
                        : "not linked"}
                    </td>
                    <td>
                      <input
                        className="price-input"
                        inputMode="decimal"
                        value={prices[String(candidate.player_id)] ?? ""}
                        placeholder="—"
                        aria-label={`Your price for ${candidate.name} in millions of euros`}
                        onChange={(event) => {
                          const next = {
                            ...prices,
                            [String(candidate.player_id)]: event.target.value.replace(/[^0-9.]/g, ""),
                          };
                          setPrices(next);
                          remember("squad-prices", JSON.stringify(next));
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <EmptyState title="No candidates to price">
          Add candidates to a shortlist and they will appear here.
        </EmptyState>
      )}
    </section>
  );
}
