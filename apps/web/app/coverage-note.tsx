"use client";

import { useEffect, useState } from "react";
import { API } from "./components";

type Row = { season_label: string; qualified_players: number; competitions: number };

/** Plain-language answer to "why isn't this player here?". */
export function CoverageNote() {
  const [rows, setRows] = useState<Row[]>([]);
  useEffect(() => {
    void fetch(`${API}/coverage/seasons`)
      .then((response) => response.json())
      .then((payload: { data: Row[] }) => setRows(payload.data))
      .catch(() => setRows([]));
  }, []);
  const top = [...rows].sort((a, b) => b.qualified_players - a.qualified_players).slice(0, 6);
  return (
    <details className="coverage-note">
      <summary>What players and seasons does this cover?</summary>
      <p>
        <b>Event profiles</b> (heatmaps, pass maps, xT, archetypes, percentiles) come from free
        open event data. That data is thick for 2015/16 and 2017/18 and patchy elsewhere, and
        recent full seasons are not openly released. So a player who has mostly played since 2019,
        such as many of today's stars, may have no event profile.
      </p>
      <p>
        <b>Stats profiles</b> cover every current Premier League player (totals, expected stats,
        injury news and rankings) from the public Premier League feed. Current La Liga players
        have a lighter stats profile (season totals and per-90 rankings) from a free third-party
        feed. Neither has event locations.
      </p>
      {top.length ? (
        <p className="coverage-chips">
          Most event coverage:{" "}
          {top.map((row) => (
            <span key={row.season_label}>
              {row.season_label} · {row.qualified_players.toLocaleString("en-GB")} players
            </span>
          ))}
        </p>
      ) : null}
    </details>
  );
}
