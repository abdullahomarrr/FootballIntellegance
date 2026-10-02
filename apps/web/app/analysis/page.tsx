"use client";

import { useEffect, useRef, useState } from "react";
import { API, EmptyState, formatNumber, ordinal, PitchHeatmap } from "../components";
import { HistoricalCompare } from "../historical-compare";
import { euros } from "../market-panel";
import { StatusMessage } from "../page-loader";

type SearchRow = {
  player_id: number;
  name: string;
  team: string;
  team_id: number;
  league_name: string;
  role: string | null;
  age: number | null;
};
type Card = {
  player_id: number;
  name: string;
  team: string | null;
  team_id: number | null;
  league: string | null;
  season: string | null;
  position: string | null;
  family: string;
  family_label: string;
  birth_date: string | null;
  height: string | null;
  foot: string | null;
  contract_end: string | null;
  market_value_eur: number | null;
  minutes: number;
  matches: number | null;
  goals: number | null;
  assists: number | null;
  rating: number | null;
  heatmap: { x_bin: number; y_bin: number; events: number }[];
  heatmap_points: number;
};
type StatRow = {
  key: string;
  title: string;
  a_per90: number | null;
  b_per90: number | null;
  a_percentile: number | null;
  b_percentile: number | null;
  lower_is_better: boolean;
  winner: "a" | "b" | "even" | null;
};
type Tally = { a: number; b: number; even: number };
type HeadToHead = {
  a: Card;
  b: Card;
  comparable: boolean;
  same_role?: boolean;
  similarity?: number | null;
  summary?: Tally & { compared: number };
  biggest_edges?: { a: StatRow[]; b: StatRow[] };
  radar: { key: string; title: string; a: number | null; b: number | null }[];
  groups: { group: string; tally: Tally; stats: StatRow[] }[];
  low_minutes?: string[];
};

const photo = (id: number) => `https://images.fotmob.com/image_resources/playerimages/${id}.png`;
const crest = (id: number) => `https://images.fotmob.com/image_resources/logo/teamlogo/${id}_small.png`;
const surname = (name: string) => name.split(" ").slice(-1)[0];

export default function ComparePage() {
  const [mode, setMode] = useState<"current" | "historical">("current");
  return (
    <main className="product-page" id="workspace-content">
      <div className="page-head">
        <div>
          <div className="eyebrow">Player comparison</div>
          <h1 className="page-title">Compare players</h1>
          <p className="lede">
            Put two players side by side: who ranks higher, by how much, and where each one
            has the edge.
          </p>
        </div>
      </div>
      <div className="view-tabs" role="tablist" aria-label="Comparison data">
        <button
          role="tab"
          aria-selected={mode === "current"}
          className={mode === "current" ? "active" : ""}
          onClick={() => setMode("current")}
        >
          This season
        </button>
        <button
          role="tab"
          aria-selected={mode === "historical"}
          className={mode === "historical" ? "active" : ""}
          onClick={() => setMode("historical")}
        >
          Historical event data
        </button>
      </div>
      {mode === "current" ? <CurrentCompare /> : <HistoricalCompare />}
    </main>
  );
}

function CurrentCompare() {
  const [picked, setPicked] = useState<{ a: SearchRow | null; b: SearchRow | null }>({ a: null, b: null });
  const [result, setResult] = useState<HeadToHead | null>(null);
  const [note, setNote] = useState("");
  const [state, setState] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const a = Number(params.get("a")), b = Number(params.get("b"));
    if (a && b) void run(a, b);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(a: number, b: number) {
    setState("Comparing…");
    try {
      const response = await fetch(`${API}/compare/current?a=${a}&b=${b}`);
      if (!response.ok) throw new Error(String(response.status));
      const payload = await response.json();
      setResult(payload.data);
      setNote(payload.meta?.method_note ?? "");
      setState("");
      window.history.replaceState(null, "", `/analysis?a=${a}&b=${b}`);
    } catch {
      setState("Could not load this comparison. One of the player pages may be unavailable.");
    }
  }
  function choose(side: "a" | "b", row: SearchRow) {
    const next = { ...picked, [side]: row };
    setPicked(next);
    if (next.a && next.b && next.a.player_id !== next.b.player_id) void run(next.a.player_id, next.b.player_id);
  }
  function swap() {
    setPicked({ a: picked.b, b: picked.a });
    if (result) void run(result.b.player_id, result.a.player_id);
  }

  return (
    <>
      <section className="panel h2h-pickers">
        <CurrentSearch label="First player" chosen={picked.a?.name ?? result?.a.name} onSelect={(row) => choose("a", row)} />
        <button className="h2h-swap" onClick={swap} disabled={!result} aria-label="Swap players" title="Swap players">
          ⇄
        </button>
        <CurrentSearch label="Second player" chosen={picked.b?.name ?? result?.b.name} onSelect={(row) => choose("b", row)} />
      </section>
      <StatusMessage message={state} />
      {result ? (
        <HeadToHeadView data={result} note={note} />
      ) : !state ? (
        <EmptyState title="Pick two players" icon="↔">
          Any current player in the Premier League, La Liga, Serie A, Bundesliga or Ligue 1. Try
          Saka and Raphinha.
        </EmptyState>
      ) : null}
    </>
  );
}

function CurrentSearch({
  label,
  chosen,
  onSelect,
}: {
  label: string;
  chosen?: string;
  onSelect: (row: SearchRow) => void;
}) {
  const [term, setTerm] = useState("");
  const [rows, setRows] = useState<SearchRow[]>([]);
  const [open, setOpen] = useState(false);
  const timer = useRef<number>(0);
  useEffect(() => {
    window.clearTimeout(timer.current);
    if (term.trim().length < 2) {
      setRows([]);
      return;
    }
    timer.current = window.setTimeout(() => {
      void fetch(`${API}/squads/search?q=${encodeURIComponent(term.trim())}&limit=6`)
        .then((response) => (response.ok ? response.json() : { data: [] }))
        .then((payload) => setRows(payload.data ?? []))
        .catch(() => setRows([]));
    }, 220);
  }, [term]);
  return (
    <label className="h2h-search">
      <span>{label}</span>
      <input
        value={term}
        placeholder={chosen ?? "Search a current player…"}
        onChange={(event) => {
          setTerm(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {open && rows.length ? (
        <div className="h2h-results" role="listbox">
          {rows.map((row) => (
            <button
              type="button"
              key={row.player_id}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                onSelect(row);
                setTerm("");
                setOpen(false);
              }}
            >
              <img src={crest(row.team_id)} alt="" width={20} height={20} />
              <span>
                <b>{row.name}</b>
                <small>
                  {row.team} · {row.role ?? "Position unclear"}
                  {row.age ? ` · ${row.age}` : ""}
                </small>
              </span>
            </button>
          ))}
        </div>
      ) : null}
    </label>
  );
}

function HeadToHeadView({ data, note }: { data: HeadToHead; note: string }) {
  const [group, setGroup] = useState(0);
  const { a, b } = data;
  if (!data.comparable)
    return (
      <EmptyState title="Not enough stats to compare">
        One of these players has no per-90 stats this season yet, so there is nothing fair to
        compare. Missing data is not counted as zero.
      </EmptyState>
    );
  const summary = data.summary!;
  const leader =
    summary.a === summary.b ? null : summary.a > summary.b ? a.name : b.name;
  const current = data.groups[Math.min(group, data.groups.length - 1)];
  return (
    <>
      <section className="panel h2h-head">
        <PlayerCard card={a} side="a" />
        <div className="h2h-score" aria-label="Stats won by each player">
          <strong>
            <span className="side-a">{summary.a}</span>
            <i>–</i>
            <span className="side-b">{summary.b}</span>
          </strong>
          <small>
            {leader ? `${surname(leader)} leads` : "Level"} on {summary.compared} stats ·{" "}
            {summary.even} even
          </small>
          {data.similarity != null ? <em>{Math.round(data.similarity)}% similar profiles</em> : null}
        </div>
        <PlayerCard card={b} side="b" />
      </section>

      {data.low_minutes?.length ? (
        <div className="notice">
          {data.low_minutes.join(" and ")} {data.low_minutes.length > 1 ? "have" : "has"} under
          450 minutes this season, so a couple of matches can still swing these numbers.
        </div>
      ) : null}
      {!data.same_role ? (
        <div className="notice">
          Different roles: {a.name} is ranked against {a.family_label}, {b.name} against{" "}
          {b.family_label}. A higher percentile means better for their own role, not that one
          would do the other&apos;s job better.
        </div>
      ) : null}

      <section className="panel h2h-overview">
        <div>
          <div className="eyebrow">Shape of their game</div>
          <h2>Role profile</h2>
          <Radar axes={data.radar} a={a.name} b={b.name} />
        </div>
        <div className="h2h-edges">
          <div className="eyebrow">Where the gap is biggest</div>
          <h2>Clear edges</h2>
          <EdgeList title={`${a.name} is better at`} side="a" rows={data.biggest_edges?.a ?? []} />
          <EdgeList title={`${b.name} is better at`} side="b" rows={data.biggest_edges?.b ?? []} />
        </div>
      </section>

      <section className="panel">
        <div className="card-top">
          <div>
            <div className="eyebrow">Stat by stat</div>
            <h2>Who ranks higher</h2>
          </div>
          <span className="tag">Per 90 · percentile within role</span>
        </div>
        <div className="h2h-groups" role="tablist">
          {data.groups.map((item, index) => (
            <button
              key={item.group}
              role="tab"
              aria-selected={index === group}
              className={index === group ? "active" : ""}
              onClick={() => setGroup(index)}
            >
              {item.group}
              <small>
                <span className="side-a">{item.tally.a}</span>–<span className="side-b">{item.tally.b}</span>
              </small>
            </button>
          ))}
        </div>
        <div className="h2h-rows">
          <div className="h2h-row h2h-row-head">
            <span>{a.name}</span>
            <span />
            <span>{b.name}</span>
          </div>
          {current.stats.map((row) => (
            <StatLine key={row.key} row={row} />
          ))}
        </div>
        <p className="research-note">
          Bars show each player&apos;s percentile in their role (longer is better
          {current.stats.some((row) => row.lower_is_better) ? "; for stats like dispossessed, fewer is better and the bar already accounts for that" : ""}).
          A dash means the stat isn&apos;t recorded for that player.
        </p>
      </section>

      <section className="panel">
        <div className="eyebrow">Where they play</div>
        <h2>Touch maps this season</h2>
        <div className="two-col h2h-maps">
          {[a, b].map((card) => (
            <div key={card.player_id}>
              <h3>{card.name}</h3>
              {card.heatmap.length ? (
                <PitchHeatmap cells={card.heatmap} events={card.heatmap_points} caption={`${card.team ?? ""} · attacking left to right`} />
              ) : (
                <p className="research-note">No touch map for {card.name} yet.</p>
              )}
            </div>
          ))}
        </div>
      </section>
      <p className="research-note">{note} Source: FotMob player pages (local use only).</p>
    </>
  );
}

function PlayerCard({ card, side }: { card: Card; side: "a" | "b" }) {
  const [noPhoto, setNoPhoto] = useState(false);
  const age = card.birth_date ? Math.floor((Date.now() - Date.parse(card.birth_date)) / 31557600000) : null;
  return (
    <article className={`h2h-card side-${side}`}>
      <div className="h2h-photo">
        {noPhoto ? (
          <span>{card.name.split(" ").map((p) => p[0]).join("").slice(0, 2)}</span>
        ) : (
          <img src={photo(card.player_id)} alt={card.name} onError={() => setNoPhoto(true)} />
        )}
        {card.team_id ? <img className="h2h-crest" src={crest(card.team_id)} alt="" /> : null}
      </div>
      <h2>{card.name}</h2>
      <p>
        {card.team} · {card.position ?? "Position unclear"}
      </p>
      <dl>
        <div>
          <dt>Age</dt>
          <dd>{age ?? "—"}</dd>
        </div>
        <div>
          <dt>Minutes</dt>
          <dd>{formatNumber(card.minutes, 0)}</dd>
        </div>
        <div>
          <dt>G / A</dt>
          <dd>
            {card.goals ?? 0} / {card.assists ?? 0}
          </dd>
        </div>
        <div>
          <dt>Rating</dt>
          <dd>{card.rating ? formatNumber(card.rating, 2) : "—"}</dd>
        </div>
        <div>
          <dt>Value</dt>
          <dd>{card.market_value_eur ? euros(card.market_value_eur) : "—"}</dd>
        </div>
        <div>
          <dt>Contract</dt>
          <dd>{card.contract_end ? card.contract_end.slice(0, 4) : "—"}</dd>
        </div>
      </dl>
    </article>
  );
}

function EdgeList({ title, side, rows }: { title: string; side: "a" | "b"; rows: StatRow[] }) {
  return (
    <div className={`h2h-edge-list side-${side}`}>
      <h3>{title}</h3>
      {rows.length ? (
        rows.map((row) => (
          <div key={row.key}>
            <span>{row.title}</span>
            <b>
              {ordinal(Math.round(side === "a" ? row.a_percentile! : row.b_percentile!))} vs{" "}
              {ordinal(Math.round(side === "a" ? row.b_percentile! : row.a_percentile!))}
            </b>
          </div>
        ))
      ) : (
        <p>No stat where they rank clearly higher.</p>
      )}
    </div>
  );
}

function StatLine({ row }: { row: StatRow }) {
  const value = (v: number | null) => (v == null ? "—" : formatNumber(v, 2));
  const bar = (pct: number | null, side: "a" | "b") => (
    <div className={`h2h-bar side-${side} ${row.winner === side ? "won" : ""}`}>
      <i style={{ width: `${pct == null ? 0 : Math.max(2, pct)}%` }} />
    </div>
  );
  return (
    <div className={`h2h-row winner-${row.winner ?? "none"}`}>
      <div className="h2h-cell side-a">
        <b>{value(row.a_per90)}</b>
        <small>{row.a_percentile == null ? "" : ordinal(Math.round(row.a_percentile))}</small>
        {bar(row.a_percentile, "a")}
      </div>
      <span className="h2h-title">
        {row.title}
        {row.lower_is_better ? <small>fewer is better</small> : null}
      </span>
      <div className="h2h-cell side-b">
        {bar(row.b_percentile, "b")}
        <small>{row.b_percentile == null ? "" : ordinal(Math.round(row.b_percentile))}</small>
        <b>{value(row.b_per90)}</b>
      </div>
    </div>
  );
}

function Radar({
  axes,
  a,
  b,
}: {
  axes: { key: string; title: string; a: number | null; b: number | null }[];
  a: string;
  b: string;
}) {
  if (axes.length < 3) return <p className="research-note">Not enough shared stats for a role profile.</p>;
  const size = 340, c = size / 2, r = 118;
  const point = (i: number, pct: number) => {
    const angle = (Math.PI * 2 * i) / axes.length - Math.PI / 2;
    return [c + Math.cos(angle) * r * (pct / 100), c + Math.sin(angle) * r * (pct / 100)];
  };
  const shape = (side: "a" | "b") =>
    axes.map((axis, i) => point(i, axis[side] ?? 0).join(",")).join(" ");
  return (
    <figure className="h2h-radar">
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Role profile of ${a} and ${b}`}>
        {[25, 50, 75, 100].map((ring) => (
          <polygon
            key={ring}
            points={axes.map((_, i) => point(i, ring).join(",")).join(" ")}
            className="ring"
          />
        ))}
        {axes.map((axis, i) => {
          const [x, y] = point(i, 100);
          const [lx, ly] = point(i, 122);
          return (
            <g key={axis.key}>
              <line x1={c} y1={c} x2={x} y2={y} className="spoke" />
              <text x={lx} y={ly} textAnchor={Math.abs(lx - c) < 8 ? "middle" : lx > c ? "start" : "end"} dominantBaseline="middle">
                {axis.title}
              </text>
            </g>
          );
        })}
        <polygon points={shape("a")} className="area side-a" />
        <polygon points={shape("b")} className="area side-b" />
      </svg>
      <figcaption>
        <span className="key side-a">{a}</span>
        <span className="key side-b">{b}</span>
        Percentile in role · outer ring is the best in the top five leagues
      </figcaption>
    </figure>
  );
}
