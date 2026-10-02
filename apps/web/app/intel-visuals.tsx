"use client";

import { useState } from "react";
import { formatNumber, PitchHeatmap, ShotMap } from "./components";

type Cell = { x_bin: number; y_bin: number; events: number };
type Shot = {
  x_m: number;
  y_m: number;
  outcome?: string | null;
  shot_xg?: number | null;
};

/** Metrics shown on the radar for each broad position, in clockwise order. */
export const RADAR_AXES: Record<string, string[]> = {
  FW: [
    "xg_per_90",
    "average_shot_xg",
    "box_entries_per_90",
    "successful_dribbles_per_90",
    "progressive_carries_per_90",
    "xt_added_per_90",
    "progressive_passes_per_90",
    "pressures_per_90",
  ],
  MD: [
    "progressive_passes_per_90",
    "passes_into_final_third_per_90",
    "pass_completion_pct",
    "progressive_carries_per_90",
    "xt_added_per_90",
    "recoveries_per_90",
    "defensive_duels_per_90",
    "pressures_per_90",
  ],
  DF: [
    "progressive_passes_per_90",
    "pass_completion_pct",
    "pressured_pass_completion_pct",
    "progressive_carries_per_90",
    "turnovers_per_90",
    "recoveries_per_90",
    "defensive_actions_per_90",
    "defensive_duels_per_90",
  ],
  GK: [
    "goalkeeper_save_pct",
    "goalkeeper_saves_per_90",
    "goals_conceded_per_90",
    "claims_and_punches_per_90",
    "sweeper_actions_per_90",
    "goalkeeper_distribution_pct",
    "goalkeeper_long_pass_pct",
  ],
};

export function RadarChart({
  axes,
  title,
}: {
  axes: { label: string; value: number }[];
  title: string;
}) {
  const size = 320;
  const center = size / 2;
  const radius = 108;
  const count = axes.length;
  const point = (index: number, fraction: number) => {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
    return [
      center + Math.cos(angle) * radius * fraction,
      center + Math.sin(angle) * radius * fraction,
    ] as const;
  };
  const polygon = axes
    .map((axis, index) => point(index, Math.max(0.02, axis.value / 100)).join(","))
    .join(" ");
  return (
    <figure className="radar-figure">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`${title}: ${axes
          .map((axis) => `${axis.label} ${Math.round(axis.value)}th percentile`)
          .join(", ")}`}
      >
        {[0.25, 0.5, 0.75, 1].map((ring) => (
          <polygon
            key={ring}
            className="radar-ring"
            points={axes.map((_, index) => point(index, ring).join(",")).join(" ")}
          />
        ))}
        {axes.map((axis, index) => {
          const [x, y] = point(index, 1);
          const [lx, ly] = point(index, 1.2);
          return (
            <g key={axis.label}>
              <line className="radar-spoke" x1={center} y1={center} x2={x} y2={y} />
              <text
                className="radar-label"
                x={lx}
                y={ly}
                textAnchor={lx < center - 8 ? "end" : lx > center + 8 ? "start" : "middle"}
                dominantBaseline="middle"
              >
                {axis.label}
              </text>
            </g>
          );
        })}
        <polygon className="radar-area" points={polygon} />
        {axes.map((axis, index) => {
          const [x, y] = point(index, Math.max(0.02, axis.value / 100));
          return (
            <circle key={axis.label} className="radar-dot" cx={x} cy={y} r={3.5}>
              <title>{`${axis.label}: ${Math.round(axis.value)}th percentile`}</title>
            </circle>
          );
        })}
      </svg>
      <figcaption>
        Each spoke is a peer percentile; the outer ring is the 100th. Larger area means
        more favourable evidence, not a better player overall.
      </figcaption>
    </figure>
  );
}

export function ProfileFitBars({
  fits,
  primary,
  secondary,
}: {
  fits: { name: string; score: number }[];
  primary?: string;
  secondary?: string | null;
}) {
  if (!fits.length) return null;
  return (
    <div className="fit-bars" aria-label="Fit against each tactical profile">
      <div className="eyebrow">Fit against each profile</div>
      {fits.map((fit) => (
        <div
          className={`fit-row${fit.name === primary ? " fit-first" : fit.name === secondary ? " fit-second" : ""}`}
          key={fit.name}
        >
          <span>{fit.name}</span>
          <div className="fit-track">
            <i style={{ width: `${Math.max(2, Math.min(100, fit.score))}%` }} />
          </div>
          <b>{formatNumber(fit.score, 0)}</b>
        </div>
      ))}
    </div>
  );
}

const LAYERS = [
  { key: "all", label: "All actions" },
  { key: "passes", label: "Passes" },
  { key: "carries", label: "Carries & dribbles" },
  { key: "defensive", label: "Defensive actions" },
] as const;

const ORIENTATION_NOTE =
  "The team attacks left to right. Both providers record locations relative to the team's own direction: over 99% of shots in the database fall in the attacking third in both halves.";

export function LayeredHeatmap({
  all,
  layers,
  columns,
  rows,
}: {
  all: Cell[];
  layers: Record<string, Cell[]>;
  columns: number;
  rows: number;
}) {
  const [layer, setLayer] = useState<(typeof LAYERS)[number]["key"]>("all");
  const cells = layer === "all" ? all : (layers[layer] ?? []);
  const total = cells.reduce((sum, cell) => sum + Number(cell.events), 0);
  return (
    <div className="layered-map">
      <div className="layer-tabs" role="tablist" aria-label="Action layer">
        {LAYERS.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={layer === item.key}
            className={layer === item.key ? "active" : ""}
            onClick={() => setLayer(item.key)}
            disabled={item.key !== "all" && !(layers[item.key]?.length)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <PitchHeatmap
        cells={cells}
        columns={columns}
        rows={rows}
        events={total}
        caption={`Darker areas show where more of these recorded actions occurred. ${ORIENTATION_NOTE}`}
        label="Attacking direction →"
      />
    </div>
  );
}

export function ThreatMap({
  cells,
  columns,
  rows,
  total,
}: {
  cells: Cell[];
  columns: number;
  rows: number;
  total?: number | null;
}) {
  if (!cells.length) return null;
  return (
    <div className="threat-map">
      <div className="eyebrow">Expected threat (xT)</div>
      <h3>Where the player moves the ball into danger</h3>
      <PitchHeatmap
        cells={cells}
        columns={columns}
        rows={rows}
        tone="threat"
        unit="threat created"
        caption={`Each zone sums the threat gained by completed passes and carries that started there, using a transparent location-value model (it rises toward goal and through central lanes). Net threat added this sample: ${formatNumber(total, 1)}. ${ORIENTATION_NOTE}`}
        label="Attacking direction →"
      />
    </div>
  );
}

export function FilterableShotMap({ shots }: { shots: Shot[] }) {
  const [mode, setMode] = useState<"all" | "goals" | "quality">("all");
  const isGoal = (shot: Shot) => String(shot.outcome ?? "").toLowerCase().includes("goal");
  const shown = shots.filter((shot) =>
    mode === "goals" ? isGoal(shot) : mode === "quality" ? Number(shot.shot_xg) >= 0.2 : true,
  );
  return (
    <div className="layered-map">
      <div className="layer-tabs" role="tablist" aria-label="Shot filter">
        {(
          [
            ["all", "All shots"],
            ["goals", "Goals"],
            ["quality", "Big chances (xG ≥ 0.20)"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={mode === key}
            className={mode === key ? "active" : ""}
            onClick={() => setMode(key)}
          >
            {label}
          </button>
        ))}
      </div>
      <ShotMap shots={shown} />
    </div>
  );
}

export function DifferenceBars({
  differences,
}: {
  differences: Record<
    string,
    { target_percentile: number; candidate_percentile: number; difference: number }
  >;
}) {
  const entries = Object.entries(differences ?? {})
    .sort((a, b) => Math.abs(b[1].difference) - Math.abs(a[1].difference))
    .slice(0, 4);
  if (!entries.length) return null;
  return (
    <div className="diff-bars" aria-label="Largest percentile differences">
      {entries.map(([metric, value]) => (
        <div className="diff-row" key={metric}>
          <span>{metric.replace(/_per_90|_pct/g, "").replace(/_/g, " ")}</span>
          <div className="diff-track">
            <i
              className="diff-target"
              style={{ left: `${Math.max(0, Math.min(100, value.target_percentile))}%` }}
              title={`Target ${Math.round(value.target_percentile)}th`}
            />
            <i
              className="diff-candidate"
              style={{ left: `${Math.max(0, Math.min(100, value.candidate_percentile))}%` }}
              title={`Candidate ${Math.round(value.candidate_percentile)}th`}
            />
          </div>
        </div>
      ))}
      <p className="diff-legend">
        <i className="diff-target" /> this player · <i className="diff-candidate" /> candidate
      </p>
    </div>
  );
}

export function ScopeNote({
  scope,
  population,
  position,
}: {
  scope?: string | null;
  population?: number | null;
  position?: string | null;
}) {
  if (!scope) return null;
  const pooled = scope === "POOLED_PROVIDER_POSITION";
  return (
    <p className={`scope-note${pooled ? " pooled" : ""}`}>
      <b>{pooled ? "Wider comparison pool" : "Like-for-like cohort"}</b>
      {pooled
        ? ` · ranked against ${formatNumber(population, 0)} qualified ${position ?? ""} player-seasons from the same data provider across all competitions and seasons, because this league season has too few qualified peers to rank fairly.`
        : ` · ranked against ${formatNumber(population, 0)} qualified ${position ?? ""} players in the same competition and season (900+ minutes).`}
    </p>
  );
}

export type TacticalContextData = {
  team_name: string;
  competition_name: string;
  season_label: string;
  style: string;
  style_strength: string;
  team_player_count: number;
  axes: {
    axis: string;
    label: string;
    description: string;
    team_score: number | null;
    player_score: number | null;
    delta: number | null;
  }[];
  adds: string[];
  relies: string[];
  notes: string[];
};

export function TacticalContextCard({
  data,
  playerName,
}: {
  data: TacticalContextData;
  playerName: string;
}) {
  return (
    <div className="tactical-card">
      <div className="tactical-style">
        <span className="eyebrow">
          {data.team_name} · {data.season_label}
        </span>
        <h3>
          {data.style}
          <span className={`clarity-chip ${data.style_strength === "DISTINCT" ? "" : "blended"}`}>
            {data.style_strength === "DISTINCT" ? "Distinct style" : "Blended style"}
          </span>
        </h3>
        <p className="analysis-copy">
          Built from {data.team_player_count} qualified squad players, each ranked against
          same-position peers. Bars compare the squad average with {playerName}.
        </p>
      </div>
      <div className="tactical-axes">
        {data.axes.map((axis) => (
          <div className="tactical-axis" key={axis.axis}>
            <div className="tactical-axis-head">
              <b>{axis.label}</b>
              {axis.delta !== null ? (
                <span className={axis.delta >= 10 ? "up" : axis.delta <= -10 ? "down" : ""}>
                  {axis.delta > 0 ? "+" : ""}
                  {formatNumber(axis.delta, 0)} vs squad
                </span>
              ) : null}
            </div>
            <div className="diff-track tactical-track">
              {axis.team_score !== null ? (
                <i
                  className="diff-target"
                  style={{ left: `${Math.max(0, Math.min(100, axis.team_score))}%` }}
                  title={`Squad average ${Math.round(axis.team_score)}`}
                />
              ) : null}
              {axis.player_score !== null ? (
                <i
                  className="diff-candidate"
                  style={{ left: `${Math.max(0, Math.min(100, axis.player_score))}%` }}
                  title={`Player ${Math.round(axis.player_score)}`}
                />
              ) : null}
            </div>
          </div>
        ))}
        <p className="diff-legend">
          <i className="diff-target" /> squad average · <i className="diff-candidate" /> {playerName}
        </p>
      </div>
      <div className="report-columns tactical-reads">
        <div>
          <h3>What the player adds to this system</h3>
          {data.adds.length ? (
            data.adds.map((item) => (
              <p className="report-claim positive" key={item}>
                {item}
              </p>
            ))
          ) : (
            <p className="analysis-copy">Nothing sits clearly above the squad norm.</p>
          )}
        </div>
        <div>
          <h3>Where the squad carries the load</h3>
          {data.relies.length ? (
            data.relies.map((item) => (
              <p className="report-claim risk" key={item}>
                {item}
              </p>
            ))
          ) : (
            <p className="analysis-copy">No clear gap relative to the squad norm.</p>
          )}
        </div>
      </div>
      <p className="research-note">{data.notes.join(" ")}</p>
    </div>
  );
}

export type PassLine = {
  x_m: number;
  y_m: number;
  end_x_m: number;
  end_y_m: number;
  completed: boolean;
};

export function PassMap({
  passes,
  goalkeeper,
}: {
  passes: PassLine[];
  goalkeeper: boolean;
}) {
  const [show, setShow] = useState<"all" | "completed" | "failed">("all");
  if (!passes.length) return null;
  const completed = passes.filter((pass) => pass.completed).length;
  const shown = passes.filter((pass) =>
    show === "completed" ? pass.completed : show === "failed" ? !pass.completed : true,
  );
  return (
    <div className="threat-map pass-map">
      <div className="eyebrow">{goalkeeper ? "Distribution map" : "Progressive passing"}</div>
      <h3>
        {goalkeeper
          ? "Where the goalkeeper's long passes go"
          : "Passes that move the ball into the final third"}
      </h3>
      <div className="layer-tabs" role="tablist" aria-label="Pass outcome">
        {(
          [
            ["all", `All ${passes.length}`],
            ["completed", `Completed ${completed}`],
            ["failed", `Not completed ${passes.length - completed}`],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={show === key}
            className={show === key ? "active" : ""}
            onClick={() => setShow(key)}
          >
            {label}
          </button>
        ))}
      </div>
      <figure className="heatmap-figure">
        <div
          className="pitch heatmap-pitch passmap-pitch"
          aria-label={`${shown.length} passes drawn from start to end location`}
        >
          <div className="pitch-line half" />
          <div className="pitch-circle" />
          <div className="box left" />
          <div className="box right" />
          <svg viewBox="0 0 105 68" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <marker id="arrow-ok" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
                <path d="M0,0 L4,2 L0,4 z" fill="#a9efca" />
              </marker>
              <marker id="arrow-miss" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
                <path d="M0,0 L4,2 L0,4 z" fill="#ffb199" />
              </marker>
            </defs>
            {shown.map((pass, index) => (
              <line
                key={index}
                x1={pass.x_m}
                y1={pass.y_m}
                x2={pass.end_x_m}
                y2={pass.end_y_m}
                stroke={pass.completed ? "#a9efca" : "#ffb199"}
                strokeOpacity={pass.completed ? 0.85 : 0.55}
                strokeWidth={0.45}
                markerEnd={pass.completed ? "url(#arrow-ok)" : "url(#arrow-miss)"}
              />
            ))}
          </svg>
          <span className="pitch-label">Attacking direction →</span>
        </div>
        <figcaption>
          {goalkeeper
            ? "The 150 longest passes (30 m or more). Green arrows reached a teammate; orange arrows did not."
            : "The 150 most forward completed and attempted passes that end in the final third. Green arrows reached a teammate; orange arrows did not."}{" "}
          Locations are oriented so the team attacks left to right.
        </figcaption>
      </figure>
    </div>
  );
}

export type RoleFitRow = {
  role_id: number;
  name: string;
  fit_score: number;
  coverage_pct: number;
  drivers: { metric: string; percentile: number }[];
  gaps: { metric: string; percentile: number }[];
};

export function RoleFitList({
  fits,
  label,
}: {
  fits: RoleFitRow[];
  label: (metric: string) => string;
}) {
  return (
    <div className="rolefit-list">
      {fits.map((fit) => (
        <article className="rolefit-row" key={fit.role_id}>
          <div className="rolefit-head">
            <h3>{fit.name}</h3>
            <b>{formatNumber(fit.fit_score, 0)}</b>
          </div>
          <div className="fit-track light">
            <i style={{ width: `${Math.max(2, Math.min(100, fit.fit_score))}%` }} />
          </div>
          <p>
            Driven by{" "}
            {fit.drivers.map((item) => `${label(item.metric)} (${item.percentile}th)`).join(" and ")}
            {fit.gaps.length
              ? `; held back by ${fit.gaps
                  .map((item) => `${label(item.metric)} (${item.percentile}th)`)
                  .join(" and ")}`
              : ""}
            . {fit.coverage_pct}% of the brief's priorities are measurable for this player.
          </p>
        </article>
      ))}
    </div>
  );
}

export function CopyBriefButton({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      // Some embedded or non-secure contexts block the async clipboard API.
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const copied = document.execCommand("copy");
      document.body.removeChild(area);
      setState(copied ? "copied" : "failed");
    }
    window.setTimeout(() => setState("idle"), 2500);
  }
  return (
    <button type="button" className="copy-brief" onClick={() => void copy()}>
      {state === "copied" ? "Copied ✓" : state === "failed" ? "Copy failed" : "Copy scouting brief"}
    </button>
  );
}
