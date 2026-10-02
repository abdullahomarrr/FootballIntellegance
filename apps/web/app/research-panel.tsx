"use client";

import { useEffect, useState } from "react";
import { API, EmptyState, type Envelope } from "./components";
import { InlineLoader } from "./page-loader";

type Claim = {
  category: string;
  statement: string;
  value?: string | null;
  source_name: string;
  source_url: string;
  source_published_at?: string | null;
  retrieved_at: string;
  evidence_quote: string;
  extractor: string;
  label: string;
  confidence: string;
};
type Source = { source: string; status: string; detail?: string | null; item_count: number };
type Article = {
  title: string;
  url: string;
  source?: string;
  published_at?: string | null;
};
type Research = {
  query: string;
  search_url?: string;
  articles: Article[];
  claims?: Claim[];
  sources?: Source[];
  retrieved_at?: string;
  extractor?: string;
  disclaimer?: string;
  error_message?: string | null;
};

const GROUPS: { key: string; title: string }[] = [
  { key: "INJURY", title: "Injury / availability" },
  { key: "CONTRACT", title: "Contract" },
  { key: "TRANSFER", title: "Transfer & fee" },
  { key: "MARKET_VALUE", title: "Market value" },
  { key: "CURRENT_CLUB", title: "Club" },
  { key: "FORM", title: "Form" },
];
const SOURCE_LABEL: Record<string, string> = {
  google_news_rss: "Google News headlines",
  wikipedia: "Wikipedia",
};
const STATUS_LABEL: Record<string, string> = {
  OK: "reachable",
  UNAVAILABLE: "not responding",
  NO_RESULTS: "nothing found",
};

function day(value?: string | null) {
  if (!value) return "date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "date unavailable"
    : date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
function time(value?: string | null) {
  if (!value) return "just now";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "just now"
    : date.toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
}

export function ResearchPanel({
  playerId,
  playerName,
}: {
  playerId: number | string;
  playerName: string;
}) {
  const [state, setState] = useState<
    | { phase: "loading" }
    | { phase: "error"; message: string }
    | { phase: "ready"; payload: Envelope<Research> }
  >({ phase: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ phase: "loading" });
    fetch(`${API}/players/${playerId}/research`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Research service returned ${response.status}`);
        return response.json() as Promise<Envelope<Research>>;
      })
      .then((payload) => setState({ phase: "ready", payload }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          phase: "error",
          message: error instanceof Error ? error.message : "Could not reach the research service",
        });
      });
    return () => controller.abort();
  }, [playerId]);

  const data = state.phase === "ready" ? state.payload.data : null;
  const claims = data?.claims ?? [];

  return (
    <section className="panel research-panel" aria-live="polite">
      <div className="eyebrow">Latest news · not verified by us</div>
      <h2>Latest news about {playerName}</h2>
      <p className="analysis-copy">
        Fetched just now from a short list of public news sources. Each item links to where it
        came from, so check the source before relying on it.
      </p>

      {state.phase === "loading" ? (
        <InlineLoader label="Checking the latest headlines…" />
      ) : null}

      {state.phase === "error" ? (
        <EmptyState title="Could not load current context">
          {state.message}. The rest of the profile is unaffected; try again in a minute.
        </EmptyState>
      ) : null}

      {data ? (
        <>
          <div className="research-sources" role="list">
            {(data.sources ?? []).map((source) => (
              <span
                role="listitem"
                key={source.source}
                className={`research-chip ${source.status === "OK" ? "ok" : "down"}`}
                title={source.detail ?? undefined}
              >
                {SOURCE_LABEL[source.source] ?? source.source} ·{" "}
                {STATUS_LABEL[source.status] ?? source.status}
              </span>
            ))}
            {data.retrieved_at ? (
              <span className="research-chip">Retrieved {time(data.retrieved_at)}</span>
            ) : null}
          </div>

          {claims.length === 0 ? (
            <EmptyState title="No clear claims found">
              {data.error_message ??
                "None of the sources stated an injury, contract, transfer, value or form point we could quote. Open the headlines below to read further."}
            </EmptyState>
          ) : (
            GROUPS.map((group) => {
              const rows = claims.filter((claim) => claim.category === group.key);
              if (!rows.length) return null;
              return (
                <div className="research-group" key={group.key}>
                  <h3>{group.title}</h3>
                  {rows.map((claim, index) => (
                    <article className="claim-card" key={`${claim.source_url}-${index}`}>
                      <div className="claim-head">
                        <strong>{claim.statement}</strong>
                        {claim.value ? <span className="claim-value">{claim.value}</span> : null}
                      </div>
                      <blockquote>“{claim.evidence_quote}”</blockquote>
                      <div className="claim-meta">
                        <a href={claim.source_url} target="_blank" rel="noreferrer">
                          {claim.source_name} ↗
                        </a>
                        <span>
                          {claim.source_name === "Wikipedia" ? "Page last edited" : "Published"}{" "}
                          {day(claim.source_published_at)}
                        </span>
                        <span>Retrieved {time(claim.retrieved_at)}</span>
                        <span className="claim-badge">Unverified public estimate</span>
                      </div>
                    </article>
                  ))}
                </div>
              );
            })
          )}

          {claims.length > 0 &&
          GROUPS.some((group) => !claims.some((claim) => claim.category === group.key)) ? (
            <p className="research-note">
              Nothing was found in these sources for:{" "}
              {GROUPS.filter((group) => !claims.some((claim) => claim.category === group.key))
                .map((group) => group.title.toLowerCase())
                .join(", ")}
              . Reliable market values, fees and contract terms need a licensed source, so absence here
              does not mean there is nothing to find.
            </p>
          ) : null}

          {data.articles.length ? (
            <div className="research-group">
              <h3>Headlines</h3>
              <div className="research-list">
                {data.articles.slice(0, 8).map((article) => (
                  <article className="research-card" key={article.url}>
                    <div>
                      <small>
                        {article.source ?? "Publisher unavailable"} · {day(article.published_at)}
                      </small>
                      <h3>{article.title}</h3>
                    </div>
                    <a className="text-link" href={article.url} target="_blank" rel="noreferrer">
                      Read source ↗
                    </a>
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {data.search_url ? (
            <p className="analysis-copy">
              <a className="text-link" href={data.search_url} target="_blank" rel="noreferrer">
                Open live news search ↗
              </a>
            </p>
          ) : null}
        </>
      ) : null}

      <p className="research-note">
        These claims are context for a human reader only. They never feed performance scores,
        percentiles, similarity or any model.
      </p>
    </section>
  );
}
