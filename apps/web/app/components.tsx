"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Player = {
  player_id: number;
  canonical_name: string;
  birth_date?: string | null;
  nationality_codes?: string[];
  preferred_foot?: string | null;
  provider_count?: number;
  position_group?: string | null;
  minutes_played?: number | null;
  appearances?: number | null;
  season_label?: string | null;
  season_status?: string | null;
  competition_name?: string | null;
  team_name?: string | null;
  sample_confidence?: string | null;
};
export type Envelope<T> = { data: T; meta?: Record<string, unknown> };

export function formatNumber(value: unknown, digits = 1) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n)
    ? new Intl.NumberFormat("en-GB", { maximumFractionDigits: digits }).format(
        n,
      )
    : "—";
}

export function ordinal(value: unknown) {
  if (value == null || value === "") return "—";
  const n = Math.round(Number(value));
  if (!Number.isFinite(n)) return "—";
  const mod100 = n % 100;
  const suffix =
    mod100 >= 11 && mod100 <= 13
      ? "th"
      : n % 10 === 1
        ? "st"
        : n % 10 === 2
          ? "nd"
          : n % 10 === 3
            ? "rd"
            : "th";
  return `${n}${suffix}`;
}

const METRIC_LABELS: Record<string, string> = {
  pass_completion_pct: "Pass completion",
  pressured_pass_completion_pct: "Passing under pressure",
  progressive_passes_per_90: "Progressive passes",
  passes_into_final_third_per_90: "Final-third entries",
  box_entries_per_90: "Penalty-area entries",
  progressive_carries_per_90: "Progressive carries",
  successful_dribbles_per_90: "Successful dribbles",
  pressures_per_90: "Pressures",
  recoveries_per_90: "Ball recoveries",
  defensive_actions_per_90: "Defensive actions",
  defensive_duels_per_90: "Defensive duels",
  turnovers_per_90: "Ball security",
  xt_added_per_90: "Threat added (xT)",
  xg_per_90: "Expected goals",
  average_shot_xg: "Shot quality",
  goalkeeper_saves_per_90: "Save volume",
  goalkeeper_save_pct: "Save percentage",
  goals_conceded_per_90: "Goals-conceded record",
  claims_and_punches_per_90: "Claims and punches",
  sweeper_actions_per_90: "Sweeper actions",
  goalkeeper_distribution_pct: "Distribution accuracy",
  goalkeeper_long_pass_pct: "Long-pass accuracy",
};

export function humanize(value: string) {
  return (
    METRIC_LABELS[value] ??
    value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

export function ageFrom(date?: string | null) {
  if (!date) return null;
  const born = new Date(date);
  const now = new Date();
  return (
    now.getFullYear() -
    born.getFullYear() -
    (now < new Date(now.getFullYear(), born.getMonth(), born.getDate()) ? 1 : 0)
  );
}

export function EmptyState({
  title,
  children,
  icon = "○",
}: {
  title: string;
  children: React.ReactNode;
  icon?: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">{icon}</span>
      <div>
        <strong style={{ color: "var(--ink)" }}>{title}</strong>
        <p>{children}</p>
      </div>
    </div>
  );
}

export function Stat({
  label,
  value,
  detail,
}: {
  label: string;
  value: React.ReactNode;
  detail?: string;
}) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </div>
  );
}

export function Percentile({
  label,
  value,
  raw,
}: {
  label: string;
  value: number;
  raw?: unknown;
}) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="percentile">
      <div>
        <span>{humanize(label)}</span>
        <span>
          {raw == null ? ordinal(v) : `${formatNumber(raw, 2)} · ${ordinal(v)}`}
        </span>
      </div>
      <div className="bar">
        <i style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

export function Pitch({
  x,
  y,
  events,
}: {
  x?: number | null;
  y?: number | null;
  events?: number;
}) {
  const left = `${Math.max(3, Math.min(97, ((x ?? 52.5) / 105) * 100))}%`;
  const top = `${Math.max(5, Math.min(95, ((y ?? 34) / 68) * 100))}%`;
  return (
    <div
      className="pitch"
      aria-label="Average event position on a football pitch"
    >
      <div className="pitch-line half" />
      <div className="pitch-circle" />
      <div className="box left" />
      <div className="box right" />
      <div className="heat" style={{ left, top }}>
        <i />
        <i />
        <i />
      </div>
      <span className="pitch-label">Attacking direction →</span>
      {events ? (
        <span className="event-count">
          {formatNumber(events, 0)} located events
        </span>
      ) : null}
    </div>
  );
}

type HeatCell = { x_bin: number; y_bin: number; events: number };
type ShotPoint = {
  x_m: number;
  y_m: number;
  outcome?: string | null;
  shot_xg?: number | null;
};

export function PitchHeatmap({
  cells,
  columns = 12,
  rows = 8,
  events,
  tone = "heat",
  caption,
  label = "Attacking direction →",
  unit = "located actions",
}: {
  cells?: HeatCell[];
  columns?: number;
  rows?: number;
  events?: number;
  tone?: "heat" | "threat";
  caption?: string;
  label?: string;
  unit?: string;
}) {
  const valid = (cells ?? []).filter(
    (cell) => Number.isFinite(Number(cell.events)) && Number(cell.events) > 0,
  );
  const maximum = Math.max(1, ...valid.map((cell) => Number(cell.events)));
  return (
    <figure className="heatmap-figure">
      <div
        className="pitch heatmap-pitch"
        aria-label={`Event-density map based on ${formatNumber(events, 0)} ${unit}`}
      >
        <div className="pitch-line half" />
        <div className="pitch-circle" />
        <div className="box left" />
        <div className="box right" />
        <div
          className="heatmap-grid"
          style={{
            gridTemplateColumns: `repeat(${columns},1fr)`,
            gridTemplateRows: `repeat(${rows},1fr)`,
          }}
          aria-hidden="true"
        >
          {Array.from({ length: columns * rows }, (_, index) => {
            const x = index % columns;
            const y = Math.floor(index / columns);
            const cell = valid.find(
              (item) => Number(item.x_bin) === x && Number(item.y_bin) === y,
            );
            const intensity = cell
              ? Math.sqrt(Number(cell.events) / maximum)
              : 0;
            return (
              <span
                key={`${x}-${y}`}
                style={{
                  background: intensity
                    ? `${tone === "threat" ? "rgba(255,213,79," : "rgba(224,70,35,"}${(0.12 + intensity * 0.82).toFixed(3)})`
                    : "transparent",
                }}
              />
            );
          })}
        </div>
        <span className="pitch-label">{label}</span>
        {events && tone === "heat" ? (
          <span className="event-count">
            {formatNumber(events, 0)} {unit}
          </span>
        ) : null}
      </div>
      <figcaption>
        {caption ??
          "Darker areas show where more recorded actions occurred. The team attacks left to right."}
      </figcaption>
    </figure>
  );
}

export function ShotMap({ shots }: { shots?: ShotPoint[] }) {
  const valid = (shots ?? [])
    .filter(
      (shot) =>
        Number.isFinite(Number(shot.x_m)) && Number.isFinite(Number(shot.y_m)),
    )
    .slice(-250);
  const goals = valid.filter((shot) =>
    String(shot.outcome ?? "")
      .toLowerCase()
      .includes("goal"),
  ).length;
  return (
    <figure className="shotmap-figure">
      <div
        className="pitch shotmap-pitch"
        aria-label={`Shot map showing ${valid.length} attempts and ${goals} goals`}
      >
        <div className="pitch-line half" />
        <div className="pitch-circle" />
        <div className="box left" />
        <div className="box right" />
        {valid.map((shot, index) => {
          const goal = String(shot.outcome ?? "")
            .toLowerCase()
            .includes("goal");
          const xg = Number(shot.shot_xg);
          const size = Number.isFinite(xg)
            ? 6 + Math.sqrt(Math.max(0, xg)) * 15
            : 8;
          return (
            <i
              className={goal ? "shot goal" : "shot"}
              key={index}
              title={`${goal ? "Goal" : "Shot"}${Number.isFinite(xg) ? ` · ${formatNumber(xg, 2)} xG` : ""}`}
              style={{
                left: `${Math.max(2, Math.min(98, (Number(shot.x_m) / 105) * 100))}%`,
                top: `${Math.max(3, Math.min(97, (Number(shot.y_m) / 68) * 100))}%`,
                width: size,
                height: size,
              }}
            />
          );
        })}
        <span className="pitch-label">Attacking direction →</span>
        <span className="event-count">
          {valid.length} shots · {goals} goals
        </span>
      </div>
      <figcaption>
        Circle size represents expected-goal value when the provider supplies
        it. Filled circles are recorded goals; outlined circles are other
        attempts.
      </figcaption>
    </figure>
  );
}

export function TrendChart({ rows }: { rows: Record<string, unknown>[] }) {
  // Keep team/competition samples separate: combining them could double-count coverage.
  const samples = rows
    .map((row, index) => ({
      key: `${row.season_id}-${row.team_id}-${row.competition_id}-${index}`,
      label: String(row.season_label ?? "Season unavailable"),
      context: [row.team_name, row.competition_name]
        .filter(Boolean)
        .join(" · "),
      minutes:
        row.minutes_played == null || row.minutes_played === ""
          ? null
          : Number(row.minutes_played),
      year: Number(String(row.season_label ?? "").match(/^\d{4}/)?.[0]) || 0,
    }))
    .sort((a, b) => a.year - b.year || a.label.localeCompare(b.label));
  const valid = samples.filter(
    (row) =>
      row.minutes !== null && Number.isFinite(row.minutes) && row.minutes >= 0,
  );
  if (!valid.length)
    return (
      <EmptyState title="Season minutes unavailable">
        No recorded minutes are available for these season samples.
      </EmptyState>
    );
  const maximum = Math.max(0, ...valid.map((row) => row.minutes!));
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, maximum)));
  const step = magnitude / 2;
  const ceiling = Math.max(1, Math.ceil(maximum / step) * step);
  return (
    <figure
      className="season-chart"
      aria-label="Recorded minutes by season sample"
    >
      <div className="season-chart-scale" aria-hidden="true">
        <span>Season</span>
        <div>
          <span>0</span>
          <span>{formatNumber(ceiling / 2, 0)}</span>
          <span>{formatNumber(ceiling, 0)}</span>
        </div>
        <span>Minutes</span>
      </div>
      <ol>
        {samples.map((sample) => {
          const available =
            sample.minutes !== null &&
            Number.isFinite(sample.minutes) &&
            sample.minutes >= 0;
          return (
            <li key={sample.key}>
              <div className="season-chart-label">
                <strong>{sample.label}</strong>
                {sample.context && <small>{sample.context}</small>}
              </div>
              <div className="season-chart-track" aria-hidden="true">
                {available && (
                  <span
                    className="season-chart-fill"
                    style={{ width: `${(sample.minutes! / ceiling) * 100}%` }}
                  >
                    <i />
                  </span>
                )}
              </div>
              <span className="season-chart-value">
                {available ? formatNumber(sample.minutes, 0) : "—"}
                <span className="sr-only">
                  {available ? " recorded minutes" : " Minutes unavailable"}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
      <figcaption>
        Minutes in the available match sample, not necessarily a full season.
        Missing seasons are not plotted.
      </figcaption>
    </figure>
  );
}

export function PlayerSearch({
  onSelect,
  label = "Choose a player",
}: {
  onSelect: (player: Player) => void;
  label?: string;
}) {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState<Player[]>([]);
  const [open, setOpen] = useState(false);
  const committedQuery = useRef<string | null>(null);
  useEffect(() => {
    if (committedQuery.current === query) {
      committedQuery.current = null;
      return;
    }
    const timer = setTimeout(async () => {
      if (query.trim().length < 2) {
        setPlayers([]);
        return;
      }
      try {
        const r = await fetch(
          `${API}/players?limit=8&search=${encodeURIComponent(query)}`,
        );
        const p = await r.json();
        setPlayers(p.data ?? []);
        setOpen(true);
      } catch {
        setPlayers([]);
      }
    }, 220);
    return () => clearTimeout(timer);
  }, [query]);
  return (
    <div className="search-box">
      <span>{label}</span>
      <div className="search-input">
        <b>⌕</b>
        <input
          aria-label={label}
          value={query}
          onChange={(e) => {
            committedQuery.current = null;
            setQuery(e.target.value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") setOpen(false);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search by player name…"
        />
      </div>
      {open && players.length > 0 && (
        <div className="search-results">
          {players.map((p) => (
            <button
              type="button"
              key={p.player_id}
              onClick={() => {
                committedQuery.current = p.canonical_name;
                setQuery(p.canonical_name);
                setOpen(false);
                onSelect(p);
              }}
            >
              <span className="avatar">
                {p.canonical_name.slice(0, 2).toUpperCase()}
              </span>
              <span>
                <strong>{p.canonical_name}</strong>
                <small>
                  {p.nationality_codes?.join(" · ") || "Player profile"}
                </small>
              </span>
              <b>→</b>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Methodology({ meta }: { meta?: Record<string, unknown> }) {
  const useful = useMemo(
    () => Object.entries(meta ?? {}).filter(([, v]) => v != null),
    [meta],
  );
  if (!useful.length) return null;
  return (
    <details className="methodology">
      <summary>Data &amp; methodology</summary>
      <dl>
        {useful.map(([k, v]) => (
          <div key={k}>
            <dt>{humanize(k)}</dt>
            <dd>
              {Array.isArray(v)
                ? v.join(", ")
                : typeof v === "object"
                  ? "Available in source record"
                  : String(v)}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
