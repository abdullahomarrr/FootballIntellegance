"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { API } from "./components";
import { PageLoader } from "./page-loader";

const QUICK_MS = 2500;
const POLL_MS = 3000;
const EXPECTED_S = 45;

type Phase = "checking" | "ready" | "waking" | "failed";

async function ping(timeoutMs: number) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API}/health`, { signal: controller.signal, cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * The hosted API sleeps when idle and takes ~30-60s to wake. Ping it on first load; if it is
 * slow, cover workspace pages with a short explainer until it answers, then reload so the
 * page's own requests run against the awake API. The landing page only pings silently.
 */
export default function ApiWakeup() {
  const path = usePathname();
  const [phase, setPhase] = useState<Phase>("checking");
  const [seconds, setSeconds] = useState(0);
  const shown = useRef(false);
  const onWorkspace = path !== "/";
  const visible = onWorkspace && (phase === "waking" || phase === "failed");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (await ping(QUICK_MS)) {
        if (!cancelled) setPhase("ready");
        return;
      }
      if (cancelled) return;
      setPhase("waking");
      const started = Date.now();
      while (!cancelled) {
        if (await ping(10_000)) {
          if (cancelled) return;
          setPhase("ready");
          if (shown.current) window.location.reload();
          return;
        }
        if (Date.now() - started > 150_000) {
          if (!cancelled) setPhase("failed");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (visible) shown.current = true;
  }, [visible]);

  useEffect(() => {
    if (phase !== "waking") return;
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, [phase]);

  if (!visible) return null;
  const progress = Math.min(95, Math.round((seconds / EXPECTED_S) * 100));
  if (phase === "failed")
    return (
      <PageLoader label="The data server isn't answering">
        <p className="page-loader-hint">It may be restarting. Try again in a minute.</p>
        <button className="action" onClick={() => window.location.reload()}>
          Try again
        </button>
      </PageLoader>
    );
  return (
    <PageLoader label="Warming up the pitch…">
      <p className="page-loader-hint">
        The data server naps when nobody&apos;s around. It&apos;s waking up now, which usually
        takes under a minute. The page will load by itself.
      </p>
      <div className="wakeup-bar" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>
      <small className="page-loader-hint">{seconds}s</small>
    </PageLoader>
  );
}
