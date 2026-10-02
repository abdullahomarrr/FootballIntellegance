"use client";

import { EmptyState } from "./components";

type Valuation = { valuation_date: string; amount: number | string };
type Transfer = {
  transfer_date: string;
  from_club_name?: string | null;
  to_club_name?: string | null;
  transfer_season?: string | null;
  fee_amount?: number | string | null;
  raw_fee_text?: string | null;
};
export type MarketData = {
  market_values: Valuation[];
  transfers: Transfer[];
  contract?: { contract_expires: string; club_name?: string | null; observed_as_of: string } | null;
  link?: { match_basis: string; tm_name?: string | null } | null;
};

export function euros(value: number | string | null | undefined) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  if (amount >= 1_000_000) return `€${(amount / 1_000_000).toFixed(amount >= 100_000_000 ? 0 : 1)}m`;
  if (amount >= 1_000) return `€${Math.round(amount / 1_000)}k`;
  return `€${Math.round(amount)}`;
}

const day = (value: string) =>
  new Date(value).toLocaleDateString("en-GB", { month: "short", year: "numeric" });

const BASIS: Record<string, string> = {
  NAME_AND_BIRTH_DATE: "Linked by full name and birth date",
  NAME_AND_NATIONALITY: "Probable link: name, nationality and position agree",
  SAME_PERSON_OTHER_PROVIDER: "Linked through the same person's other provider record",
};

/** End of the season (30 June of the second year) a label like "2017/18" refers to. */
function seasonEnd(label?: string) {
  const match = /^(\d{4})[/-]/.exec(label ?? "");
  return match ? new Date(Date.UTC(Number(match[1]) + 1, 5, 30)) : null;
}

function Timeline({ values, season }: { values: Valuation[]; season?: string }) {
  const points = values
    .map((v) => ({ t: new Date(v.valuation_date).getTime(), v: Number(v.amount) }))
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v));
  if (points.length < 2) return null;
  const width = 640;
  const height = 220;
  const pad = { left: 52, right: 16, top: 14, bottom: 26 };
  const minT = points[0].t;
  const maxT = points[points.length - 1].t;
  const rawMax = Math.max(...points.map((p) => p.v));
  const step = rawMax <= 20_000_000 ? 5_000_000 : rawMax <= 100_000_000 ? 25_000_000 : 50_000_000;
  const maxV = Math.ceil((rawMax * 1.02) / step) * step;
  const x = (t: number) => pad.left + ((t - minT) / Math.max(1, maxT - minT)) * (width - pad.left - pad.right);
  const y = (v: number) => pad.top + (1 - v / maxV) * (height - pad.top - pad.bottom);
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const area = `${path} L${x(maxT)},${height - pad.bottom} L${x(minT)},${height - pad.bottom} Z`;
  const peak = points.reduce((a, b) => (b.v > a.v ? b : a));
  const end = seasonEnd(season)?.getTime();
  const marked = end && end >= minT && end <= maxT ? end : null;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => maxV * f);
  const years = Array.from(
    new Set(points.map((p) => new Date(p.t).getUTCFullYear())),
  ).filter((_, i, all) => i % Math.ceil(all.length / 6) === 0);
  return (
    <svg
      className="value-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Market value from ${euros(points[0].v)} to ${euros(points[points.length - 1].v)}, peak ${euros(peak.v)}`}
    >
      {ticks.map((tick) => (
        <g key={tick}>
          <line className="radar-spoke" x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} />
          <text className="radar-label" x={pad.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle">
            {euros(tick)}
          </text>
        </g>
      ))}
      {years.map((year) => (
        <text
          key={year}
          className="radar-label"
          x={x(Date.UTC(year, 0, 1) < minT ? minT : Date.UTC(year, 0, 1))}
          y={height - 8}
          textAnchor="middle"
        >
          {year}
        </text>
      ))}
      <path className="value-area" d={area} />
      <path className="value-line" d={path} />
      {marked ? (
        <g>
          <line className="value-marker" x1={x(marked)} x2={x(marked)} y1={pad.top} y2={height - pad.bottom} />
          <text className="radar-label" x={x(marked)} y={pad.top + 2} textAnchor="middle">
            {season}
          </text>
        </g>
      ) : null}
      <circle className="value-peak" cx={x(peak.t)} cy={y(peak.v)} r={4} />
      <text className="radar-label" x={x(peak.t)} y={y(peak.v) - 9} textAnchor="middle">
        peak {euros(peak.v)}
      </text>
    </svg>
  );
}

export function MarketPanel({
  data,
  sourceLabel,
  season,
}: {
  data: MarketData | undefined;
  sourceLabel?: string;
  season?: string;
}) {
  const values = data?.market_values ?? [];
  const transfers = [...(data?.transfers ?? [])].reverse();
  if (!values.length && !transfers.length) {
    return (
      <EmptyState title="No market data linked">
        This player could not be matched to the historical snapshot with enough confidence, so no
        value is shown rather than a guess.
      </EmptyState>
    );
  }
  const cutoff = seasonEnd(season)?.getTime();
  const atSeason = cutoff
    ? [...values].reverse().find((v) => new Date(v.valuation_date).getTime() <= cutoff)
    : undefined;
  const latest = values[values.length - 1];
  const peak = values.reduce((a, b) => (Number(b.amount) > Number(a.amount) ? b : a), values[0]);
  return (
    <div className="market-card">
      <div className="stat-grid market-stats">
        {atSeason ? (
          <div className="stat">
            <small>Value at end of {season}</small>
            <strong>{euros(atSeason.amount)}</strong>
            <small>{day(atSeason.valuation_date)}</small>
          </div>
        ) : null}
        <div className="stat">
          <small>Peak value</small>
          <strong>{peak ? euros(peak.amount) : "—"}</strong>
          <small>{peak ? day(peak.valuation_date) : ""}</small>
        </div>
        <div className="stat">
          <small>Last recorded</small>
          <strong>{latest ? euros(latest.amount) : "—"}</strong>
          <small>{latest ? day(latest.valuation_date) : ""}</small>
        </div>
        {data?.contract ? (
          <div className="stat">
            <small>Contract expires</small>
            <strong>{new Date(data.contract.contract_expires).getFullYear()}</strong>
            <small>as of {day(data.contract.observed_as_of)}</small>
          </div>
        ) : null}
      </div>
      <Timeline values={values} season={season} />
      {transfers.length ? (
        <div className="table-wrap">
          <table className="transfer-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>From</th>
                <th>To</th>
                <th>Fee</th>
              </tr>
            </thead>
            <tbody>
              {transfers.slice(0, 10).map((row, index) => (
                <tr key={index}>
                  <td>{day(row.transfer_date)}</td>
                  <td>{row.from_club_name ?? "—"}</td>
                  <td>{row.to_club_name ?? "—"}</td>
                  <td>{row.fee_amount ? euros(row.fee_amount) : (row.raw_fee_text ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <p className="research-note">
        {sourceLabel ?? "Third-party historical snapshot, frozen."}{" "}
        {data?.link ? `${BASIS[data.link.match_basis] ?? data.link.match_basis}${data.link.tm_name ? ` (${data.link.tm_name})` : ""}.` : ""}{" "}
        A market value is an estimate of worth, not a transfer fee, and fees are shown separately.
      </p>
    </div>
  );
}
