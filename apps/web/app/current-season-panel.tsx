"use client";

import { useEffect, useMemo, useState } from "react";
import { API, formatNumber, ordinal, PitchHeatmap, ShotMap } from "./components";
import styles from "./current-season.module.css";
import { InlineLoader } from "./page-loader";

type Stat = {
  key: string;
  title: string;
  group: string;
  per90: number | null;
  percentile_per90: number | null;
};
export type CurrentSeason = {
  player_id: number;
  name: string;
  team: string | null;
  birth_date: string | null;
  contract_end: string | null;
  height: string | null;
  foot: string | null;
  positions: { label: string; main: boolean }[];
  league: { name: string | null; season: string | null; stats: Record<string, number | string> };
  traits: { title: string; items: { key: string; title: string; value: number }[] } | null;
  stats: Stat[];
  market_values: { date: string; value: number }[];
  heatmap: [number, number][];
  shots: { x: number; y: number; xg: number | null; type: string }[];
  squad: {
    team_name: string;
    league_name: string;
    injured: boolean;
    injury_return: string | null;
    market_value_eur: number | null;
  };
};

function euros(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return value >= 1e6 ? `€${(value / 1e6).toFixed(value >= 1e7 ? 0 : 1)}m` : `€${Math.round(value / 1e3)}k`;
}

function heatCells(points: [number, number][]) {
  const counts = new Map<string, number>();
  for (const [x, y] of points) {
    const col = Math.min(11, Math.max(0, Math.floor((x / 105) * 12)));
    const row = Math.min(7, Math.max(0, Math.floor((y / 68) * 8)));
    counts.set(`${col}-${row}`, (counts.get(`${col}-${row}`) ?? 0) + 1);
  }
  return [...counts.entries()].map(([key, events]) => {
    const [x, y] = key.split("-").map(Number);
    return { x_bin: x, y_bin: y, events };
  });
}

const HEADLINE = ["Minutes played", "Goals", "Assists", "Rating", "Matches", "Started"];

export type CurrentSeasonState = { state: "loading" | "ready" | "none"; data: CurrentSeason | null };

/** Fetches the FotMob current-season view for a player; "none" when they are not in a current squad. */
export function useCurrentSeason(playerId: number): CurrentSeasonState {
  const [result, setResult] = useState<CurrentSeasonState>({ state: "loading", data: null });
  useEffect(() => {
    const controller = new AbortController();
    setResult({ state: "loading", data: null });
    void fetch(`${API}/players/${playerId}/current-season`, { signal: controller.signal })
      .then((response) => response.json() as Promise<{ data: CurrentSeason | null }>)
      .then((payload) =>
        setResult({ state: payload.data ? "ready" : "none", data: payload.data }),
      )
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setResult({ state: "none", data: null });
      });
    return () => controller.abort();
  }, [playerId]);
  return result;
}

/** Short label for the season picker, e.g. "2026/27 · Real Madrid · LaLiga · 630 min". */
export function currentSeasonLabel(data: CurrentSeason) {
  const minutes = data.league.stats["Minutes played"];
  return [
    data.league.season ?? "This season",
    data.squad.team_name,
    data.league.name ?? data.squad.league_name,
    minutes !== undefined ? `${String(minutes)} min` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** The richer FotMob view of a player who is in a current top-five-league squad. */
export function CurrentSeasonPanel({ current }: { current: CurrentSeasonState }) {
  const { state, data } = current;
  const groups = useMemo(() => {
    const result: Record<string, Stat[]> = {};
    for (const stat of data?.stats ?? []) {
      if (stat.group === "Discipline") continue;
      (result[stat.group] ??= []).push(stat);
    }
    return result;
  }, [data]);

  if (state === "none") return null;
  if (state === "loading") return <InlineLoader label="Checking this season's data…" />;
  if (!data) return null;

  const main = data.positions.find((p) => p.main) ?? data.positions[0];
  const headline = HEADLINE.filter((key) => data.league.stats[key] !== undefined);
  const latestValue = data.market_values.length
    ? data.market_values[data.market_values.length - 1].value
    : data.squad.market_value_eur;
  const facts = [
    data.birth_date ? `Born ${data.birth_date}` : null,
    data.height,
    data.foot ? `${data.foot} foot` : null,
    data.contract_end ? `Contract to ${data.contract_end.slice(0, 4)}` : null,
    latestValue ? `Value ${euros(latestValue)}` : null,
  ].filter(Boolean);
  const hasMaps = data.heatmap.length > 0 || data.shots.length > 0;
  return (
    <section className={styles.panel} aria-label="Current season">
      <header className={styles.header}>
        <div>
          <div className="eyebrow">
            This season · {data.league.name ?? data.squad.league_name} {data.league.season ?? ""}
          </div>
          <h2 className={styles.title}>
            {data.squad.team_name}
            {main ? <span> · {main.label}</span> : null}
            {data.squad.injured ? (
              <em className={styles.injury}>
                Injured{data.squad.injury_return ? ` · ${data.squad.injury_return.replace(/^About/, "about")}` : ""}
              </em>
            ) : (
              <em className={styles.fit}>Available</em>
            )}
          </h2>
          {facts.length ? <p className={styles.facts}>{facts.join(" · ")}</p> : null}
        </div>
        <span className="coverage-pill">● Live stats · FotMob</span>
      </header>
      {headline.length ? (
        <div className={styles.headline}>
          {headline.map((key) => (
            <div key={key}>
              <small>{key === "Minutes played" ? "Minutes" : key}</small>
              <strong>{String(data.league.stats[key])}</strong>
            </div>
          ))}
        </div>
      ) : null}
      <div className={hasMaps ? styles.body : `${styles.body} ${styles.noMaps}`}>
        {data.traits ? (
          <div className={styles.card}>
            <h3>{data.traits.title}</h3>
            {data.traits.items.map((item) => (
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
        {data.heatmap.length ? (
          <div className={`${styles.card} ${styles.map}`}>
            <h3>Where they play</h3>
            <PitchHeatmap
              cells={heatCells(data.heatmap)}
              events={data.heatmap.length}
              caption="All touches this season. Attacking left to right."
            />
          </div>
        ) : null}
        {data.shots.length ? (
          <div className={`${styles.card} ${styles.map}`}>
            <h3>Shots this season</h3>
            <ShotMap
              shots={data.shots.map((shot) => ({
                x_m: shot.x,
                y_m: shot.y,
                outcome: shot.type,
                shot_xg: shot.xg,
              }))}
            />
          </div>
        ) : null}
      </div>
      {Object.keys(groups).length ? (
        <div className={styles.groups}>
          {Object.entries(groups).map(([group, stats]) => (
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
        </div>
      ) : null}
      <p className={styles.note}>
        From FotMob&apos;s public pages, for personal use. Per-90 values; percentiles are
        FotMob&apos;s own.{" "}
        <a className="text-link" href="/squads">
          Compare with the squad →
        </a>
      </p>
    </section>
  );
}
