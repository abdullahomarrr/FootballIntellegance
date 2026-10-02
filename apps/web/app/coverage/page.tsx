"use client";

import { useEffect, useMemo, useState } from "react";
import { API, EmptyState, formatNumber, Methodology, Stat } from "../components";
import { PageLoader } from "../page-loader";

type OpenFootballRow = {
  competition_name: string;
  competition_code: string;
  season: string;
  fixture_count: number;
  finished_count: number;
  scheduled_count: number;
  data_as_of: string;
};
type StatsBombRow = {
  competition: {
    country_name: string;
    competition_name: string;
    season_name: string;
    match_available_360?: string | null;
  };
  match_count: number;
};
type WyscoutArticle = { title: string; license_name: string; files: { name: string; size: number }[] };
type CoveragePayload = {
  openfootball: OpenFootballRow[];
  statsbomb: StatsBombRow[];
  wyscout: { title: string; doi: string; checked_at: string; articles: WyscoutArticle[] };
  meta: Record<string, unknown>;
};

export default function CoveragePage() {
  const [payload, setPayload] = useState<CoveragePayload | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  useEffect(() => {
    fetch(`${API}/coverage/open`)
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then(setPayload)
      .catch(() => setError("Coverage data is temporarily unavailable."));
  }, []);
  const historical = useMemo(
    () =>
      (payload?.statsbomb ?? []).filter((row) =>
        `${row.competition.country_name} ${row.competition.competition_name} ${row.competition.season_name}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [payload, query],
  );
  const currentFixtures = payload?.openfootball.reduce((n, row) => n + row.fixture_count, 0) ?? 0;
  const currentResults = payload?.openfootball.reduce((n, row) => n + row.finished_count, 0) ?? 0;
  const eventMatches = payload?.statsbomb.reduce((n, row) => n + row.match_count, 0) ?? 0;

  return (
    <main className="product-page" id="workspace-content">
      <div className="page-head">
        <div>
          <div className="eyebrow">Data coverage</div>
          <h1 className="page-title">Data coverage</h1>
          <p className="lede">
            Understand the competitions, seasons and sources behind every player profile.
          </p>
        </div>
      </div>
      {error && <div className="notice">{error}</div>}
      {!payload && !error && <PageLoader label="Loading coverage…" />}
      {payload && (
        <>
          <div className="stat-grid">
            <Stat label="2026/27 fixtures" value={formatNumber(currentFixtures, 0)} detail={`${formatNumber(currentResults, 0)} completed`} />
            <Stat label="Current leagues" value={formatNumber(payload.openfootball.length, 0)} detail="Credential-free coverage" />
            <Stat label="Historical event matches" value={formatNumber(eventMatches, 0)} detail={`${payload.statsbomb.length} season samples`} />
          </div>

          <section className="section-block">
            <div className="section-title"><div><span className="kicker">Current season</span><h2>Fixtures and results</h2></div><span className="coverage-chip good">CC0 · OpenFootball</span></div>
            {payload.openfootball.length ? <div className="table-wrap"><table><thead><tr><th>Competition</th><th>Season</th><th>Fixtures</th><th>Results</th><th>Upcoming</th></tr></thead><tbody>
              {payload.openfootball.map((row) => <tr key={row.competition_code}><td><strong>{row.competition_name}</strong></td><td>{row.season}</td><td>{formatNumber(row.fixture_count, 0)}</td><td>{formatNumber(row.finished_count, 0)}</td><td>{formatNumber(row.scheduled_count, 0)}</td></tr>)}
            </tbody></table></div> : <EmptyState title="No current fixtures loaded">Run the approved OpenFootball backfill to populate this section.</EmptyState>}
          </section>

          <section className="section-block">
            <div className="section-title"><div><span className="kicker">Historical evidence</span><h2>Event-data coverage</h2></div><label className="inline-filter">Filter<input aria-label="Filter historical coverage" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="League, country or season" /></label></div>
            {historical.length ? <div className="table-wrap"><table><thead><tr><th>Competition</th><th>Season</th><th>Country</th><th>Matches</th><th>Enhanced positioning</th></tr></thead><tbody>
              {historical.map((row, index) => <tr key={`${row.competition.competition_name}-${row.competition.season_name}-${index}`}><td><strong>{row.competition.competition_name}</strong></td><td>{row.competition.season_name}</td><td>{row.competition.country_name}</td><td>{formatNumber(row.match_count, 0)}</td><td><span className={`coverage-chip ${row.competition.match_available_360 ? "good" : "muted"}`}>{row.competition.match_available_360 ? "Available" : "Standard event locations"}</span></td></tr>)}
            </tbody></table></div> : <EmptyState title="No matching coverage">Try a different league, country or season.</EmptyState>}
          </section>

          <section className="section-block">
            <div className="section-title"><div><span className="kicker">Deep historical profiles</span><h2>Wyscout open research data</h2></div><span className="coverage-chip good">CC BY 4.0</span></div>
            <div className="source-cards"><article className="source-card"><strong>Big Five 2017/18 event history</strong><p>Player, team, match and event records support per-90 profiles, role-relative rankings and spatial analysis for the licensed research season.</p><small>Open research collection · {payload.wyscout.articles.length} documented resource groups</small></article><article className="source-card"><strong>How it is used</strong><p>Historical event evidence is clearly separated from current-season fixtures. Check the season and competition before interpreting a player’s results.</p><small>Coverage varies by competition and season</small></article></div>
          </section>
          <Methodology meta={payload.meta} />
        </>
      )}
    </main>
  );
}
