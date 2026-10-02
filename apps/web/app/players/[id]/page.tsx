"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ageFrom,
  API,
  EmptyState,
  Envelope,
  formatNumber,
  humanize,
  Methodology,
  ordinal,
  Percentile,
  Stat,
  TrendChart,
} from "../../components";
import {
  DifferenceBars,
  FilterableShotMap,
  CopyBriefButton,
  LayeredHeatmap,
  type RoleFitRow,
  RoleFitList,
  PassMap,
  type PassLine,
  ProfileFitBars,
  RADAR_AXES,
  RadarChart,
  ScopeNote,
  TacticalContextCard,
  type TacticalContextData,
  ThreatMap,
} from "../../intel-visuals";
import {
  CurrentSeasonPanel,
  currentSeasonLabel,
  useCurrentSeason,
} from "../../current-season-panel";
import { MarketPanel, type MarketData } from "../../market-panel";
import { ResearchPanel } from "../../research-panel";
import { PageLoader } from "../../page-loader";

type Row = Record<string, unknown>;
type SimilarDifference = { target_percentile:number;candidate_percentile:number;difference:number };
type Similar = {
  player_id: number;
  name: string;
  team_name?: string;
  position_group?: string;
  similarity_score: number;
  minutes_played?: number;
  compared_feature_count?: number;
  target_feature_count?: number;
  feature_coverage_pct?: number;
  confidence?: string;
  season_label?: string;
  competition_name?: string;
  comparison_population?: string;
  feature_differences?: Record<string, SimilarDifference>;
};
type DevelopmentSample = {
  season_label: string;
  competition_name: string;
  team_name: string;
  percentile: number;
  metric_value: number;
  minutes: number;
};
type DevelopmentTrend = {
  metric_name: string;
  position_group: string;
  percentile_slope_per_year?: number | null;
  direction: "IMPROVING" | "DECLINING" | "STABLE" | "INSUFFICIENT_DATA";
  observations: number;
  total_minutes: number;
  confidence: string;
  samples: DevelopmentSample[];
};
const TOURNAMENT = /(Euro|World Cup|Copa America|Cup of Nations)/i;
const isTournament = (name: unknown) => TOURNAMENT.test(String(name ?? ""));

const intelligenceLabels: Record<
  string,
  { label: string; explanation: string; group: string }
> = {
  pass_completion_pct: {
    label: "Pass completion",
    explanation: "Share of attempted passes completed",
    group: "Distribution",
  },
  pressured_pass_completion_pct: {
    label: "Passing under pressure",
    explanation: "Completion when pressure is recorded",
    group: "Distribution",
  },
  progressive_passes_per_90: {
    label: "Progressive passes",
    explanation: "Passes advancing the ball at least 10 metres",
    group: "Progression",
  },
  passes_into_final_third_per_90: {
    label: "Final-third entries",
    explanation: "Passes carrying possession into the final third",
    group: "Progression",
  },
  box_entries_per_90: {
    label: "Penalty-area entries",
    explanation: "Passes or carries entering the box",
    group: "Threat",
  },
  progressive_carries_per_90: {
    label: "Progressive carries",
    explanation: "Carries advancing the ball at least 10 metres",
    group: "Progression",
  },
  successful_dribbles_per_90: {
    label: "Successful dribbles",
    explanation: "Completed take-ons per full match",
    group: "Ball carrying",
  },
  pressures_per_90: {
    label: "Pressures",
    explanation: "Recorded attempts to pressure an opponent",
    group: "Out of possession",
  },
  recoveries_per_90: {
    label: "Ball recoveries",
    explanation: "Loose or opposition balls recovered",
    group: "Out of possession",
  },
  defensive_actions_per_90: {
    label: "Defensive actions",
    explanation: "Interceptions, blocks and clearances",
    group: "Out of possession",
  },
  defensive_duels_per_90: {
    label: "Defensive duels",
    explanation: "Recorded defensive one-on-one contests",
    group: "Out of possession",
  },
  turnovers_per_90: {
    label: "Turnovers",
    explanation: "Miscontrols and dispossessions; lower is better",
    group: "Ball security",
  },
  xt_added_per_90: {
    label: "Threat added (xT)",
    explanation: "Net expected-threat gained by completed passes and carries",
    group: "Progression",
  },
  goalkeeper_save_pct: {
    label: "Save percentage",
    explanation: "Saves as a share of saves plus goals conceded",
    group: "Shot stopping",
  },
  goalkeeper_distribution_pct: {
    label: "Distribution accuracy",
    explanation: "Share of the goalkeeper's passes that find a teammate",
    group: "Distribution",
  },
  goalkeeper_long_pass_pct: {
    label: "Long-pass accuracy",
    explanation: "Completion on passes of 35 metres or more",
    group: "Distribution",
  },
  xg_per_90: {
    label: "Expected goals",
    explanation: "Shot quality accumulated per full match",
    group: "Threat",
  },
  average_shot_xg: {
    label: "Average shot quality",
    explanation: "Expected-goal value of the average attempt",
    group: "Threat",
  },
  goalkeeper_saves_per_90: {
    label: "Saves",
    explanation: "Recorded saves per full match",
    group: "Shot stopping",
  },
  goals_conceded_per_90: {
    label: "Goals conceded",
    explanation: "Goals conceded per full match; lower is better",
    group: "Shot stopping",
  },
  claims_and_punches_per_90: {
    label: "Claims & punches",
    explanation: "Recorded collection, punch and smother actions",
    group: "Area control",
  },
  sweeper_actions_per_90: {
    label: "Sweeper actions",
    explanation: "Interventions away from the goal line",
    group: "Space control",
  },
};

export default function PlayerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [identity, setIdentity] = useState<Envelope<Row> | null>(null);
  const [seasons, setSeasons] = useState<Envelope<Row[]> | null>(null);
  const [metrics, setMetrics] = useState<Envelope<Row[]> | null>(null);
  const [intelligence, setIntelligence] = useState<Envelope<Row[]> | null>(
    null,
  );
  const [report, setReport] = useState<Envelope<Row | null> | null>(null);
  const [spatial, setSpatial] = useState<Envelope<Row | null> | null>(null);
  const [similar, setSimilar] = useState<Envelope<Similar[]> | null>(null);
  const [development, setDevelopment] = useState<Envelope<DevelopmentTrend[]> | null>(null);
  const [market, setMarket] = useState<Envelope<{
    market_values: Row[];
    transfers: Row[];
  }> | null>(null);
  const [news, setNews] = useState<Envelope<Row[]> | null>(null);
  const [sentiment, setSentiment] = useState<Envelope<Row[]> | null>(null);
  const [availability, setAvailability] = useState<Envelope<Row | null> | null>(null);
  const [related, setRelated] = useState<Envelope<Row[]> | null>(null);
  const [roleFit, setRoleFit] = useState<Envelope<RoleFitRow[]> | null>(null);
  const [tactical, setTactical] = useState<Envelope<TacticalContextData | null> | null>(null);
  const [error, setError] = useState("");
  const [partialErrors, setPartialErrors] = useState<{ base: string[]; season: string[] }>({
    base: [],
    season: [],
  });
  const [selectedKey, setSelectedKey] = useState("");
  const [seasonLoading, setSeasonLoading] = useState(false);
  // "auto" opens on the current season when the player has one; the picker overrides it.
  const [mode, setMode] = useState<"auto" | "current" | "historical">("auto");
  const current = useCurrentSeason(Number(id));

  useEffect(() => {
    const controller = new AbortController();
    const endpoints = [
      ["/seasons", "season history"],
      ["/metrics", "baseline metrics"],
      ["/intelligence", "advanced event intelligence"],
      ["/development", "development trajectory"],
      ["/market", "market observations"],
      ["/news", "retained news"],
      ["/sentiment", "public context"],
      ["/related-identities", "combined provider records"],
      ["/availability", "current availability"],
    ] as const;
    setError("");
    setSelectedKey("");
    setMode("auto");
    setPartialErrors((current) => ({ ...current, base: [] }));
    void fetch(`${API}/players/${id}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json() as Promise<Envelope<Row>>;
      })
      .then((payload) => {
        if (!controller.signal.aborted) setIdentity(payload);
      })
      .catch((identityError: unknown) => {
        if (
          identityError instanceof DOMException &&
          identityError.name === "AbortError"
        )
          return;
        setError(
          "This player identity could not be loaded. Check the data service and try again.",
        );
      });
    void Promise.all(
      endpoints.map(async ([suffix, label]) => {
        try {
          const response = await fetch(`${API}/players/${id}${suffix}`, {
            signal: controller.signal,
          });
          if (!response.ok) throw new Error(`${response.status}`);
          return { suffix, label, payload: await response.json() };
        } catch (requestError) {
          if (requestError instanceof DOMException && requestError.name === "AbortError")
            return { suffix, label, aborted: true };
          return { suffix, label, failed: true };
        }
      }),
    ).then((results) => {
      if (controller.signal.aborted) return;
      const payload = new Map(
        results
          .filter((result) => "payload" in result)
          .map((result) => [result.suffix, result.payload]),
      );
      if (payload.has("/seasons")) setSeasons(payload.get("/seasons") as Envelope<Row[]>);
      if (payload.has("/metrics")) setMetrics(payload.get("/metrics") as Envelope<Row[]>);
      if (payload.has("/intelligence")) setIntelligence(payload.get("/intelligence") as Envelope<Row[]>);
      if (payload.has("/development")) setDevelopment(payload.get("/development") as Envelope<DevelopmentTrend[]>);
      if (payload.has("/market")) setMarket(payload.get("/market") as Envelope<{market_values:Row[];transfers:Row[]}>);
      if (payload.has("/news")) setNews(payload.get("/news") as Envelope<Row[]>);
      if (payload.has("/sentiment")) setSentiment(payload.get("/sentiment") as Envelope<Row[]>);
      if (payload.has("/availability")) setAvailability(payload.get("/availability") as Envelope<Row | null>);
      if (payload.has("/related-identities")) setRelated(payload.get("/related-identities") as Envelope<Row[]>);
      setPartialErrors((current) => ({
        ...current,
        base: results.filter((result) => "failed" in result).map((result) => result.label),
      }));
    });
    return () => controller.abort();
  }, [id]);

  // Everything that depends on which club-season is being viewed.
  useEffect(() => {
    const controller = new AbortController();
    const endpoints = [
      ["/scouting-report", "scouting interpretation"],
      ["/spatial", "spatial evidence"],
      ["/similar", "similar players"],
      ["/tactical-context", "team tactical context"],
      ["/role-fit", "recruitment role fit"],
    ] as const;
    const [team, competition, season] = selectedKey ? selectedKey.split("-") : [];
    const query = selectedKey
      ? `?team_id=${team}&competition_id=${competition}&season_id=${season}`
      : "";
    setSeasonLoading(true);
    setPartialErrors((current) => ({ ...current, season: [] }));
    void Promise.all(
      endpoints.map(async ([suffix, label]) => {
        try {
          const response = await fetch(`${API}/players/${id}${suffix}${query}`, {
            signal: controller.signal,
          });
          if (!response.ok) throw new Error(`${response.status}`);
          return { suffix, label, payload: await response.json() };
        } catch (requestError) {
          if (requestError instanceof DOMException && requestError.name === "AbortError")
            return { suffix, label, aborted: true };
          return { suffix, label, failed: true };
        }
      }),
    ).then((results) => {
      if (controller.signal.aborted) return;
      const payload = new Map(
        results
          .filter((result) => "payload" in result)
          .map((result) => [result.suffix, result.payload]),
      );
      setReport((payload.get("/scouting-report") as Envelope<Row | null>) ?? null);
      setSpatial((payload.get("/spatial") as Envelope<Row | null>) ?? null);
      setSimilar((payload.get("/similar") as Envelope<Similar[]>) ?? null);
      setTactical((payload.get("/tactical-context") as Envelope<TacticalContextData | null>) ?? null);
      setRoleFit((payload.get("/role-fit") as Envelope<RoleFitRow[]>) ?? null);
      setPartialErrors((current) => ({
        ...current,
        season: results.filter((result) => "failed" in result).map((result) => result.label),
      }));
      setSeasonLoading(false);
    });
    return () => controller.abort();
  }, [id, selectedKey]);

  const person = identity?.data ?? {};
  // Use the most substantial observed sample as the profile context. A tiny newer
  // spell should not hide the season for which the recruitment evidence exists.
  const latest = useMemo(() => {
    const rows = seasons?.data ?? [];
    if (selectedKey) {
      const [team, competition, season] = selectedKey.split("-");
      const match = rows.find(
        (row) =>
          String(row.team_id) === team &&
          String(row.competition_id) === competition &&
          String(row.season_id) === season,
      );
      if (match) return match;
    }
    return [...rows].sort(
      (a, b) => Number(b.minutes_played ?? 0) - Number(a.minutes_played ?? 0),
    )[0] ?? {};
  }, [seasons, selectedKey]);
  const seasonOptions = useMemo(
    () =>
      [...(seasons?.data ?? [])].sort((a, b) => {
        const left = String(b.season_label ?? "").localeCompare(String(a.season_label ?? ""));
        return left || Number(b.minutes_played ?? 0) - Number(a.minutes_played ?? 0);
      }),
    [seasons],
  );
  const selectedValue = `${latest.team_id}-${latest.competition_id}-${latest.season_id}`;
  const currentData = current.state === "ready" ? current.data : null;
  const viewingCurrent = Boolean(currentData) && mode !== "historical";
  const currentPosition =
    currentData?.positions.find((position) => position.main)?.label ??
    currentData?.positions[0]?.label;
  const showHistorical = (key?: string) => {
    setMode("historical");
    if (key !== undefined) setSelectedKey(key);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const latestMetrics = useMemo(() => {
    const season = latest.season_id;
    return (metrics?.data ?? [])
      .filter((row) => !season || Number(row.season_id) === Number(season))
      .slice(0, 8);
  }, [metrics, latest]);
  const best = [...latestMetrics]
    .sort((a, b) => Number(b.percentile) - Number(a.percentile))
    .slice(0, 3);
  const latestIntelligence = useMemo(
    () =>
      (intelligence?.data ?? []).filter(
        (row) =>
          Number(row.season_id) === Number(latest.season_id) &&
          Number(row.team_id) === Number(latest.team_id) &&
          Number(row.competition_id) === Number(latest.competition_id),
      ),
    [intelligence, latest],
  );
  const intelligenceValues = Object.fromEntries(
    latestIntelligence.map((row) => [
      String(row.metric_name),
      row.metric_value,
    ]),
  );
  const positionGroup = String(latest.position_group ?? "");
  const radarAxes = (RADAR_AXES[positionGroup] ?? [])
    .map((metric) => {
      const row = latestIntelligence.find((item) => String(item.metric_name) === metric);
      return row
        ? {
            label: intelligenceLabels[metric]?.label ?? humanize(metric),
            value: Number(row.percentile),
          }
        : null;
    })
    .filter((axis): axis is { label: string; value: number } => axis !== null);
  const scopeRow =
    latestIntelligence.find((row) => row.comparison_scope === "POOLED_PROVIDER_POSITION") ??
    latestIntelligence[0];
  const reportData = report?.data ?? {};
  const profileFits = Array.isArray(reportData.profile_fits)
    ? (reportData.profile_fits as { name: string; score: number }[])
    : [];
  const clarity = String(reportData.archetype_clarity ?? "").toLowerCase();
  const style = reportData.summary
    ? String(reportData.summary)
    : best.length
      ? `Stands out most for ${best.map((row) => String(row.metric_name).replace(/_/g, " ")).join(", ")}. Based on ${formatNumber(latest.minutes_played, 0)} observed minutes.`
      : "A playing-style summary will appear when enough qualified metric evidence is available.";
  const strengths = Array.isArray(reportData.strengths)
    ? (reportData.strengths as Row[])
    : [];
  const risks = Array.isArray(reportData.risks)
    ? (reportData.risks as Row[])
    : [];
  const caveats = Array.isArray(reportData.caveats)
    ? (reportData.caveats as string[])
    : [];
  const briefText = (() => {
    if (!report?.data) return "";
    const lines: string[] = [
      `SCOUTING BRIEF: ${String(person.canonical_name ?? "Player")}`,
      `${String(latest.team_name ?? "")} · ${String(latest.competition_name ?? "")} · ${String(latest.season_label ?? "")} · ${formatNumber(latest.minutes_played, 0)} minutes · ${positionGroup}`,
      "",
      `Profile: ${String(reportData.archetype)}${reportData.secondary_archetype ? ` (also: ${String(reportData.secondary_archetype)})` : ""}`,
      String(reportData.summary),
    ];
    if (strengths.length) lines.push("", "Strengths:", ...strengths.map((c) => `- ${String(c.text)}`));
    if (risks.length) lines.push("", "Questions to answer:", ...risks.map((c) => `- ${String(c.text)}`));
    if (tactical?.data) {
      lines.push("", `Team context (${tactical.data.team_name}): ${tactical.data.style}`);
      if (tactical.data.adds.length) lines.push(`Adds: ${tactical.data.adds.join("; ")}`);
      if (tactical.data.relies.length) lines.push(`Squad covers: ${tactical.data.relies.join("; ")}`);
    }
    if (roleFit?.data?.length)
      lines.push("", "Role fit:", ...roleFit.data.map((f) => `- ${f.name}: ${formatNumber(f.fit_score, 0)}/100`));
    if (caveats.length) lines.push("", `Limits: ${caveats.join(" ")}`);
    lines.push(
      "",
      "Evidence from event data only. Requires video, live scouting and medical/contract checks. Generated by Football Intelligence.",
    );
    return lines.join("\n");
  })();

  const deepSeason = [...seasonOptions].sort((a, b) => Number(b.minutes_played ?? 0) - Number(a.minutes_played ?? 0))[0];
  const contextSections = (
    <>
        <section className="panel">
          <div className="eyebrow">Market context · historical snapshot</div>
          <h2>Value &amp; transfer history</h2>
          <MarketPanel
            data={market?.data as MarketData | undefined}
            sourceLabel={String(market?.meta?.source_label ?? "")}
            season={String(latest.season_label ?? "")}
          />
          <Methodology meta={market?.meta} />
        </section>
        <ResearchPanel
          playerId={id}
          playerName={String(person.canonical_name ?? "this player")}
        />
        <section className="panel">
          <div className="eyebrow context-subhead">Stored context</div>
          <h2>Licensed news &amp; public conversation</h2>
          {sentiment?.data.length ? (
            <div className="stat-grid social-stats">
              {sentiment.data.slice(-3).map((row, index) => (
                <Stat
                  key={index}
                  label={String(row.aggregate_date)}
                  value={formatNumber(row.sentiment_mean, 2)}
                  detail={`${formatNumber(row.mention_count, 0)} public Bluesky posts`}
                />
              ))}
            </div>
          ) : (
            <EmptyState title="No public sentiment sample">
              Sentiment appears only when a permitted public source has
              observations for this player.
            </EmptyState>
          )}
          {news?.data.length ? (
            <div className="similar-list">
              {news.data.slice(0, 5).map((row, index) => (
                <a
                  className="similar-card"
                  href={String(row.canonical_url)}
                  key={index}
                >
                  <div>
                    <h3>{String(row.title)}</h3>
                    <p>
                      {String(row.publisher ?? "Publisher unavailable")} ·{" "}
                      {String(row.published_at ?? "Date unavailable")}
                    </p>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <p className="analysis-copy">
              No licensed news articles are linked to this player.
            </p>
          )}
          <div className="insight">
            <strong>Context only: </strong>Public-post tone is not a measure of
            football quality and may not represent the wider fanbase.
          </div>
          <Methodology meta={sentiment?.meta} />
        </section>
    </>
  );

  if ((!identity || current.state === "loading") && !error)
    return (
      <main className="product-page" id="workspace-content">
        <PageLoader label="Building player profile…" />
      </main>
    );
  return (
    <main
      className={`product-page${seasonLoading ? " season-loading" : ""}`}
      id="workspace-content"
    >
      {seasonLoading && !viewingCurrent ? <PageLoader label="Switching season…" /> : null}
      {error && <div className="notice">{error}</div>}
      {partialErrors.base.length + partialErrors.season.length > 0 && (
        <div className="notice">
          Partial profile: {[...partialErrors.base, ...partialErrors.season].join(", ")} could not be loaded. Available
          evidence remains visible and missing sections are not treated as zero.
        </div>
      )}
      <a className="text-link" href="/players">
        ← Player directory
      </a>
      <header className="profile-header">
        <div className="profile-avatar">
          {String(person.canonical_name ?? "PL")
            .slice(0, 2)
            .toUpperCase()}
        </div>
        <div>
          <div className="eyebrow">Player profile</div>
          <h1>{String(person.canonical_name ?? "Player unavailable")}</h1>
          <div className="identity-row">
            <span>
              {viewingCurrent
                ? currentData!.squad.team_name
                : String(latest.team_name ?? "Club unavailable")}
            </span>
            <span>
              {viewingCurrent && currentPosition
                ? currentPosition
                : String(latest.position_group ?? "Position unavailable")}
            </span>
            <span>
              {Array.isArray(person.nationality_codes)
                ? person.nationality_codes.join(" · ")
                : "Nationality unavailable"}
            </span>
            <span>
              {ageFrom(person.birth_date as string)
                ? `${ageFrom(person.birth_date as string)} years`
                : "Age unavailable"}
            </span>
            <span>
              {person.preferred_foot
                ? `${person.preferred_foot} foot`
                : "Foot unavailable"}
            </span>
          </div>
        </div>
        <span className="coverage-pill">
          ● {viewingCurrent ? "This season" : latestMetrics.length ? "Performance data" : "Identity only"}
        </span>
      </header>
      {seasonOptions.length + (currentData ? 1 : 0) > 1 ? (
        <label className="season-picker">
          <span>Season viewed</span>
          <select
            value={viewingCurrent ? "current" : selectedValue}
            onChange={(event) => {
              if (event.target.value === "current") {
                setMode("current");
                return;
              }
              setMode("historical");
              const best = [...seasonOptions].sort(
                (a, b) => Number(b.minutes_played ?? 0) - Number(a.minutes_played ?? 0),
              )[0];
              const bestKey = `${best.team_id}-${best.competition_id}-${best.season_id}`;
              setSelectedKey(event.target.value === bestKey ? "" : event.target.value);
            }}
          >
            {currentData ? (
              <option value="current">
                {currentSeasonLabel(currentData)} · this season · live stats
              </option>
            ) : null}
            {seasonOptions.map((row) => (
              <option
                key={`${row.team_id}-${row.competition_id}-${row.season_id}`}
                value={`${row.team_id}-${row.competition_id}-${row.season_id}`}
              >
                {String(row.season_label)} · {String(row.team_name ?? "Club unavailable")} ·{" "}
                {String(row.competition_name ?? "")} · {formatNumber(row.minutes_played, 0)} min
                {isTournament(row.competition_name)
                  ? " · tournament sample"
                  : Number(row.minutes_played ?? 0) < 900
                    ? " (small sample)"
                    : ""}
                {row.has_wyscout_events && !row.has_statsbomb_events ? " · Wyscout" : ""}
                {row.has_statsbomb_events ? " · StatsBomb" : ""}
              </option>
            ))}
          </select>
          <small>
            {currentData
              ? `This season plus ${seasonOptions.length} past season${seasonOptions.length === 1 ? "" : "s"} with full event data.`
              : `${seasonOptions.length} seasons on record. Season-by-season movement is in the development panel below.`}
          </small>
        </label>
      ) : null}
      <p className="analysis-copy">
        {viewingCurrent
          ? `${currentData!.league.name ?? currentData!.squad.league_name} · ${currentData!.league.season ?? "this season"} · Live season stats`
          : `${String(latest.competition_name ?? "Competition unavailable")} · ${String(latest.season_label ?? "Season unavailable")} · Historical performance evidence`}
      </p>
      {!viewingCurrent && isTournament(latest.competition_name) ? (
        <div className="availability-banner">
          <strong>Tournament sample</strong>
          {" "}· a handful of international matches, not a league season. The maps, shot map and
          pass map are real event data but small, and there are no percentile rankings or archetype
          because those need a full league season of minutes.
        </div>
      ) : null}
      {availability?.data && (viewingCurrent || !currentData) ? (
        <div
          className={`availability-banner ${String(availability.data.status) !== "a" ? "warn" : ""}`}
        >
          <strong>Current availability: {String(availability.data.status_label)}</strong>
          {availability.data.chance_of_playing !== null &&
          availability.data.chance_of_playing !== undefined &&
          !String(availability.data.news ?? "").includes("%")
            ? ` · ${String(availability.data.chance_of_playing)}% chance of playing next round`
            : ""}
          {availability.data.news ? ` · ${String(availability.data.news)}` : ""}
          <small>
            {String(availability.data.team)} · {String(availability.data.minutes)} min this season
            (Premier League feed).{" "}
            <a className="text-link" href={`/players/fpl/${String(availability.data.code)}`}>
              Current stats profile →
            </a>
          </small>
        </div>
      ) : null}
      {viewingCurrent ? (
        <>
          <CurrentSeasonPanel current={current} />
          {seasonOptions.length ? (
            <section className="deep-analysis-card">
              <div>
                <div className="eyebrow">Deep analysis</div>
                <h2>Style, similar players, tactics and pass maps</h2>
                <p className="analysis-copy">
                  These need full match-event data, which covers past seasons only. The most
                  complete one on record is{" "}
                  <strong>
                    {String(deepSeason?.season_label ?? "")} at {String(deepSeason?.team_name ?? "")}
                  </strong>{" "}
                  ({formatNumber(deepSeason?.minutes_played, 0)} min).
                </p>
              </div>
              <button className="action" onClick={() => showHistorical("")}>
                View deep analysis →
              </button>
            </section>
          ) : null}
          <div className="two-col">
            {contextSections}
          </div>
        </>
      ) : (
        <>
          {currentData ? (
            <button className="current-season-strip" onClick={() => setMode("current")}>
              <span className="eyebrow">This season</span>
              <span>
                Now at <b>{currentData.squad.team_name}</b> ·{" "}
                {currentData.league.name ?? currentData.squad.league_name}{" "}
                {currentData.league.season ?? ""}
                {currentData.squad.injured ? " · injured" : ""}
              </span>
              <span className="text-link">View this season →</span>
            </button>
          ) : null}
      <div className="insight">
        <strong>What to notice: </strong>
        {style} Combine this evidence with video and live scouting.
      </div>
      <section className="stat-grid">
        <Stat label="Appearances" value={formatNumber(latest.appearances, 0)} />
        <Stat label="Minutes" value={formatNumber(latest.minutes_played, 0)} />
        {latest.position_group === "GK" ? (
          <>
            <Stat
              label="Save percentage"
              value={`${formatNumber(intelligenceValues.goalkeeper_save_pct, 1)}%`}
            />
            <Stat
              label="Saves / 90"
              value={formatNumber(
                intelligenceValues.goalkeeper_saves_per_90,
                2,
              )}
            />
            <Stat
              label="Goals conceded / 90"
              value={formatNumber(intelligenceValues.goals_conceded_per_90, 2)}
            />
            <Stat
              label="Claims & punches / 90"
              value={formatNumber(
                intelligenceValues.claims_and_punches_per_90,
                2,
              )}
            />
            <Stat
              label="Distribution accuracy"
              value={`${formatNumber(intelligenceValues.goalkeeper_distribution_pct, 1)}%`}
            />
          </>
        ) : (
          <>
            <Stat label="Goals" value={formatNumber(latest.goals, 0)} />
            <Stat label="Assists" value={formatNumber(latest.assists, 0)} />
            <Stat
              label="Threat added / 90"
              value={formatNumber(intelligenceValues.xt_added_per_90, 2)}
              detail="xT, completed passes + carries"
            />
            <Stat
              label="xG / 90"
              value={formatNumber(intelligenceValues.xg_per_90, 2)}
            />
          </>
        )}
      </section>
      <div className="two-col">
        <section className="panel scouting-report-panel">
          <div className="card-top">
            <div>
              <div className="eyebrow">Explainable scouting interpretation</div>
              <h2>
                {String(reportData.archetype ?? "Archetype unavailable")}
                {clarity && clarity !== "unavailable" ? (
                  <span className={`clarity-chip ${clarity}`}>
                    {clarity === "clear"
                      ? "Clear profile"
                      : clarity === "blended"
                        ? "Blended profile"
                        : clarity === "limited"
                          ? "Limited by provider data"
                          : "No standout profile"}
                  </span>
                ) : null}
              </h2>
              {reportData.secondary_archetype ? (
                <div className="report-kicker">
                  Also shows: {String(reportData.secondary_archetype)}
                </div>
              ) : null}
            </div>
            <span className="tag">Evidence-led · human review</span>
          </div>
          {report?.data ? (
            <>
              <CopyBriefButton text={briefText} />
              <p className="report-summary">{String(reportData.summary)}</p>
              {Array.isArray(reportData.archetype_evidence) &&
              reportData.archetype_evidence.length ? (
                <div className="evidence-chips" aria-label="Metrics behind this archetype">
                  {(reportData.archetype_evidence as string[]).slice(0, 4).map((metric) => (
                    <span key={metric}>
                      {intelligenceLabels[metric]?.label ?? humanize(metric)}{" "}
                      {ordinal(
                        latestIntelligence.find((row) => String(row.metric_name) === metric)
                          ?.percentile,
                      )}
                    </span>
                  ))}
                </div>
              ) : null}
              <ProfileFitBars
                fits={profileFits}
                primary={String(reportData.archetype ?? "")}
                secondary={
                  reportData.secondary_archetype
                    ? String(reportData.secondary_archetype)
                    : null
                }
              />
              <div className="report-columns">
                <div>
                  <h3>Evidence-backed strengths</h3>
                  {strengths.length ? (
                    strengths.map((claim, index) => (
                      <p className="report-claim positive" key={index}>
                        {String(claim.text)}
                      </p>
                    ))
                  ) : (
                    <p className="analysis-copy">
                      No metric clears the strength threshold in this sample.
                    </p>
                  )}
                </div>
                <div>
                  <h3>Recruitment questions</h3>
                  {risks.length ? (
                    risks.map((claim, index) => (
                      <p className="report-claim risk" key={index}>
                        {String(claim.text)}
                      </p>
                    ))
                  ) : (
                    <p className="analysis-copy">
                      No metric falls below the review threshold in this sample.
                    </p>
                  )}
                </div>
              </div>
              {caveats.length ? (
                <p className="report-caveat">Limits: {caveats.join(" ")}</p>
              ) : null}
            </>
          ) : (
            <EmptyState title="Scouting interpretation unavailable">
              The player needs a qualified event sample before an archetype can
              be assigned.
            </EmptyState>
          )}
          <Methodology meta={report?.meta} />
        </section>
        {tactical?.data ? (
          <section className="panel tactical-panel">
            <div className="card-top">
              <div>
                <div className="eyebrow">Tactical context</div>
                <h2>How the team plays and where this player fits</h2>
              </div>
              <span className="tag">Evidence-led · human review</span>
            </div>
            <TacticalContextCard
              data={tactical.data}
              playerName={String(person.canonical_name ?? "the player")}
            />
            <Methodology meta={tactical.meta} />
          </section>
        ) : null}
        <section className="panel rolefit-panel">
          <div className="card-top">
            <div>
              <div className="eyebrow">Recruitment fit</div>
              <h2>Fit against your saved briefs</h2>
            </div>
            <a className="tag" href="/recruitment">
              Edit briefs →
            </a>
          </div>
          {roleFit?.data?.length ? (
            <RoleFitList fits={roleFit.data} label={(metric) => humanize(metric)} />
          ) : (
            <EmptyState title="No saved brief covers this player">
              Briefs are matched by position and need most of their priorities to be measurable
              for the player. Create one in Recruitment to see fit here.
            </EmptyState>
          )}
          <Methodology meta={roleFit?.meta} />
        </section>
        <section className="panel intelligence-panel">
          <div className="card-top">
            <div>
              <div className="eyebrow">Event intelligence</div>
              <h2>
                {latest.position_group === "GK"
                  ? "Goalkeeper-specific evidence"
                  : "How the player influences the game"}
              </h2>
            </div>
            <span className="tag">
              {latest.position_group === "GK"
                ? "Goalkeeper model"
                : "Outfield model"}
            </span>
          </div>
          <p className="analysis-copy">
            These measures are derived from individual event locations and
            outcomes, then ranked only against qualified players in the same
            position group.
          </p>
          {radarAxes.length >= 3 ? (
            <RadarChart
              axes={radarAxes}
              title={`${positionGroup === "GK" ? "Goalkeeper" : positionGroup} evidence profile`}
            />
          ) : null}
          {scopeRow ? (
            <ScopeNote
              scope={String(scopeRow.comparison_scope ?? "")}
              population={Number(scopeRow.comparison_population)}
              position={positionGroup}
            />
          ) : null}
          {latestIntelligence.length ? (
            <div className="intelligence-grid">
              {latestIntelligence.map((row) => {
                const info = intelligenceLabels[String(row.metric_name)] ?? {
                  label: String(row.metric_name),
                  explanation: "Event-derived evidence",
                  group: "Performance",
                };
                return (
                  <article key={String(row.metric_name)}>
                    <small>{info.group}</small>
                    <h3>{info.label}</h3>
                    <div>
                      <strong>{formatNumber(row.metric_value, 2)}</strong>
                      <span>{ordinal(row.percentile)} percentile</span>
                    </div>
                    <p>{info.explanation}</p>
                  </article>
                );
              })}
            </div>
          ) : (
            <EmptyState title="Advanced event evidence unavailable">
              This sample does not yet meet the coverage and
              comparison-population requirements for its position.
            </EmptyState>
          )}
          <Methodology meta={intelligence?.meta} />
        </section>
        {latest.position_group !== "GK" && latestIntelligence.length === 0 ? (
          <section className="panel">
            <div className="card-top">
              <div>
                <div className="eyebrow">Performance profile</div>
                <h2>Compared with positional peers</h2>
              </div>
              <span className="tag">{latestMetrics.length} metrics</span>
            </div>
            {latestMetrics.length ? (
              <div className="percentile-list">
                {latestMetrics.map((row) => (
                  <Percentile
                    key={String(row.metric_name)}
                    label={String(row.metric_name)}
                    value={Number(row.percentile)}
                    raw={row.metric_value}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="Peer comparison unavailable">
                Percentiles need a qualified competition, season and position
                sample.
              </EmptyState>
            )}
            <Methodology meta={metrics?.meta} />
          </section>
        ) : null}
        <section className="panel spatial-panel">
          <div className="card-top">
            <div>
              <div className="eyebrow">On-pitch behaviour</div>
              <h2>Where the player gets involved</h2>
            </div>
            <span className="tag">
              {String(spatial?.data?.season_label ?? "Covered sample")}
            </span>
          </div>
          {spatial?.data ? (
            <>
              <div className="spatial-grid">
              <LayeredHeatmap
                all={
                  spatial.data.heatmap as {
                    x_bin: number;
                    y_bin: number;
                    events: number;
                  }[]
                }
                layers={
                  (spatial.data.heatmap_layers ?? {}) as Record<
                    string,
                    { x_bin: number; y_bin: number; events: number }[]
                  >
                }
                columns={Number(spatial.data.grid_columns)}
                rows={Number(spatial.data.grid_rows)}
              />
              <ThreatMap
                cells={
                  (spatial.data.threat_cells ?? []) as {
                    x_bin: number;
                    y_bin: number;
                    events: number;
                  }[]
                }
                columns={Number(spatial.data.grid_columns)}
                rows={Number(spatial.data.grid_rows)}
                total={Number(spatial.data.threat_total)}
              />
              <PassMap
                passes={(spatial.data.pass_lines ?? []) as PassLine[]}
                goalkeeper={positionGroup === "GK"}
              />
              {Array.isArray(spatial.data.shots) &&
              spatial.data.shots.length ? (
                <div className="shot-profile">
                  <div className="eyebrow">Shot profile</div>
                  <h3>Where the attempts come from</h3>
                  <FilterableShotMap
                    shots={
                      spatial.data.shots as {
                        x_m: number;
                        y_m: number;
                        outcome?: string | null;
                        shot_xg?: number | null;
                      }[]
                    }
                  />
                </div>
              ) : null}
              </div>
              <div className="event-mix">
                {Object.entries(
                  (spatial.data.event_type_counts as Record<string, number>) ??
                    {},
                )
                  .slice(0, 6)
                  .map(([name, count]) => (
                    <div key={name}>
                      <span>{name}</span>
                      <strong>{formatNumber(count, 0)}</strong>
                    </div>
                  ))}
              </div>
              <p className="analysis-copy">
                {String(spatial.data.team_name ?? "Team unavailable")} ·{" "}
                {String(
                  spatial.data.competition_name ?? "Competition unavailable",
                )}{" "}
                · {formatNumber(spatial.data.minutes_played, 0)} recorded
                minutes
              </p>
            </>
          ) : (
            <EmptyState title="Pitch data unavailable">
              A density map needs event locations from a covered competition.
            </EmptyState>
          )}
          <Methodology meta={spatial?.meta} />
        </section>
        <section className="panel">
          <div className="eyebrow">Season coverage</div>
          <h2>Recorded minutes by season</h2>
          {(seasons?.data?.length ?? 0) > 0 ? (
            <TrendChart rows={seasons!.data} />
          ) : (
            <EmptyState title="Season data unavailable">
              Recorded minutes will appear when a season sample is available.
            </EmptyState>
          )}
          <Methodology meta={seasons?.meta} />
        </section>
        <section className="panel development-panel">
          <div className="card-top">
            <div>
              <div className="eyebrow">Observed development</div>
              <h2>How the evidence moved</h2>
            </div>
            <span className="tag">Trajectory · not a forecast</span>
          </div>
          <p className="analysis-copy">
            Season-to-season movement in direction-adjusted peer percentiles. A
            positive change means the player ranked more favourably in that
            metric, but a new team, role, league or peer group can also move the
            result.
          </p>
          {(development?.data.filter((trend) => trend.observations >= 2).length ?? 0) > 0 ? (
            <div className="development-list">
              {development!.data
                .filter((trend) => trend.observations >= 2)
                .slice(0, 5)
                .map((trend) => {
                  const first = trend.samples[0];
                  const last = trend.samples[trend.samples.length - 1];
                  const slope = Number(trend.percentile_slope_per_year ?? 0);
                  return (
                    <article key={`${trend.position_group}-${trend.metric_name}`}>
                      <div className="development-heading">
                        <div>
                          <small>{intelligenceLabels[trend.metric_name]?.group ?? "Performance"}</small>
                          <h3>{intelligenceLabels[trend.metric_name]?.label ?? humanize(trend.metric_name)}</h3>
                        </div>
                        <strong className={`trajectory-${trend.direction.toLowerCase()}`}>
                          {slope > 0 ? "+" : ""}{formatNumber(slope, 1)}
                          <small>percentile pts / year</small>
                        </strong>
                      </div>
                      <div className="development-journey">
                        <span>
                          <b>{formatNumber(first.percentile, 0)}th</b>
                          <small>{first.season_label} · {first.team_name}</small>
                        </span>
                        <i aria-hidden="true">→</i>
                        <span>
                          <b>{formatNumber(last.percentile, 0)}th</b>
                          <small>{last.season_label} · {last.team_name}</small>
                        </span>
                      </div>
                      <p>{trend.observations} qualified samples · {formatNumber(trend.total_minutes, 0)} evidence-minutes · {trend.confidence.toLowerCase()} confidence</p>
                    </article>
                  );
                })}
            </div>
          ) : (
            <EmptyState title="Longitudinal evidence unavailable">
              At least two qualified season samples in the same metric and
              position family are required. A single season is not a trajectory.
            </EmptyState>
          )}
          <div className="insight">
            <strong>Interpretation boundary: </strong>This describes recorded
            movement; it does not predict future improvement or isolate the
            effect of coaching, age, role or league strength.
          </div>
          <Methodology meta={development?.meta} />
        </section>
        <section className="panel">
          <div className="card-top">
            <div>
              <div className="eyebrow">Recruitment context</div>
              <h2>Similar players</h2>
            </div>
            <a className="tag" href="/recruitment">
              Compare →
            </a>
          </div>
          <div className="similar-list">
            {similar?.data?.slice(0, 5).map((row, index) => {
              const differences=Object.entries(row.feature_differences??{});
              const closest=[...differences].sort((a,b)=>Math.abs(a[1].difference)-Math.abs(b[1].difference))[0];
              const tradeoff=[...differences].sort((a,b)=>Math.abs(b[1].difference)-Math.abs(a[1].difference))[0];
              return (
              <a
                className="similar-card"
                href={`/players/${row.player_id}`}
                key={row.player_id}
              >
                <span className="avatar">{index + 1}</span>
                <div>
                  <h3>{row.name}</h3>
                  <p>
                    {row.team_name || "Club unavailable"} ·{" "}
                    {row.position_group || "Position unavailable"} ·{" "}
                    {formatNumber(row.minutes_played,0)} min
                  </p>
                  <p>
                    {formatNumber(row.compared_feature_count,0)}/{formatNumber(row.target_feature_count,0)} advanced features · {row.confidence?.toLowerCase()||"unknown"} confidence
                  </p>
                  <p>
                    {row.season_label ? `${row.season_label} · ${row.competition_name ?? ""} · ` : ""}
                    {closest?`Closest: ${humanize(closest[0]).replace("Per 90","").toLowerCase()} (${Math.abs(closest[1].difference).toFixed(1)} percentile points). `:""}
                    {tradeoff?`Largest difference: ${humanize(tradeoff[0]).replace("Per 90","").toLowerCase()} (${Math.abs(tradeoff[1].difference).toFixed(1)} points).`:"Feature trade-off unavailable."}
                  </p>
                  <DifferenceBars differences={row.feature_differences ?? {}} />
                </div>
                <div className="score">
                  {formatNumber(row.similarity_score, 0)}
                  <small>style similarity / 100</small>
                </div>
              </a>
              );
            })}
          </div>
          {similar && !similar.data.length && (
            <EmptyState title="No qualified peers yet">
              Similar players require matching league, season, position and
              minutes coverage.
            </EmptyState>
          )}
          <Methodology meta={similar?.meta} />
        </section>
        {contextSections}
      </div>
        </>
      )}
      <Methodology meta={identity?.meta} />
    </main>
  );
}
