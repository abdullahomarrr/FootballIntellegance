"use client";

import { useEffect, useState } from "react";
import styles from "./directory.module.css";
import { API, EmptyState, formatNumber } from "./components";
import { euros } from "./market-panel";

type Catalogue = Record<string, { name: string; description: string }[]>;
type Result = {
  player_id: number;
  name: string;
  team_name?: string | null;
  competition_name?: string | null;
  season_label?: string | null;
  minutes_played: number;
  fit_score: number;
  metric_coverage: number;
  is_primary_profile: boolean;
  clarity: string;
  market_value_eur?: number | null;
  evidence: { metric: string; label: string; percentile: number }[];
};

const POSITIONS: Record<string, string> = {
  FW: "Forward",
  MD: "Midfielder",
  DF: "Defender",
  GK: "Goalkeeper",
};

export function DiscoverPanel() {
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState("FW");
  const [archetype, setArchetype] = useState("");
  const [season, setSeason] = useState("");
  const [results, setResults] = useState<Result[] | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");

  useEffect(() => {
    void fetch(`${API}/discover/archetypes`)
      .then((response) => response.json())
      .then((payload: { data: Catalogue }) => setCatalogue(payload.data))
      .catch(() => setState("error"));
  }, []);

  const options = catalogue?.[position] ?? [];
  const selected = archetype || options[0]?.name || "";
  const description = options.find((item) => item.name === selected)?.description;

  async function search() {
    if (!selected) return;
    setState("loading");
    try {
      const query = new URLSearchParams({ position, archetype: selected, limit: "12" });
      if (season.trim()) query.set("season", season.trim());
      const response = await fetch(`${API}/discover?${query}`);
      if (!response.ok) throw new Error(String(response.status));
      const payload = (await response.json()) as { data: Result[] };
      setResults(payload.data);
      setState("idle");
    } catch {
      setState("error");
    }
  }

  return (
    <section className="panel discover-panel" aria-label="Discover players by playing style">
      <button
        type="button"
        className={styles.toggle}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span>
          <span className="eyebrow">Discover by playing style</span>
          <b>Find players who play a particular way</b>
        </span>
        <span className="tag">{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <>
      <form
        className="workflow directory-filters discover-form"
        onSubmit={(event) => {
          event.preventDefault();
          void search();
        }}
      >
        <label>
          Position
          <select
            value={position}
            onChange={(event) => {
              setPosition(event.target.value);
              setArchetype("");
              setResults(null);
            }}
          >
            {Object.entries(POSITIONS).map(([value, label]) => (
              <option value={value} key={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Playing style
          <select value={selected} onChange={(event) => setArchetype(event.target.value)}>
            {options.map((item) => (
              <option value={item.name} key={item.name}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Season (optional)
          <input
            value={season}
            onChange={(event) => setSeason(event.target.value)}
            placeholder="e.g. 2017/18"
          />
        </label>
        <button
          style={{ gridRow: "auto", gridColumn: "auto" }}
          disabled={!selected || state === "loading"}
        >
          {state === "loading" ? "Searching…" : "Find players"}
        </button>
      </form>
      {description ? <p className="analysis-copy">{description}</p> : null}
      {state === "error" ? (
        <div className="notice">Discovery is temporarily unavailable. Check the API connection.</div>
      ) : null}
      {results && results.length === 0 ? (
        <EmptyState title="No strong matches">
          No qualified player-season fits this style at 60 or above. Try another season or style.
        </EmptyState>
      ) : null}
      {results && results.length > 0 ? (
        <div className="discover-results">
          {results.map((row, index) => (
            <a className="similar-card" href={`/players/${row.player_id}`} key={row.player_id}>
              <span className="avatar">{index + 1}</span>
              <div>
                <h3>{row.name}</h3>
                <p>
                  {row.team_name ?? "Club unavailable"} · {row.competition_name ?? ""} ·{" "}
                  {row.season_label ?? ""} · {formatNumber(row.minutes_played, 0)} min
                </p>
                <div className="evidence-chips discover-chips">
                  {row.evidence.map((item) => (
                    <span key={item.metric}>
                      {item.label} {item.percentile}th
                    </span>
                  ))}
                </div>
                <p>
                  {row.is_primary_profile
                    ? "Main profile"
                    : "Secondary strength, not their main profile"}{" "}
                  · {row.metric_coverage}% metric coverage
                  {row.market_value_eur ? ` · valued ${euros(row.market_value_eur)} then` : ""}
                  {row.clarity === "LIMITED" ? " · limited by provider data" : ""}
                </p>
              </div>
              <div className="score">
                {formatNumber(row.fit_score, 0)}
                <small>style fit / 100</small>
              </div>
            </a>
          ))}
        </div>
      ) : null}
        </>
      ) : null}
    </section>
  );
}
