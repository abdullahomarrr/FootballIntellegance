"use client";

import type { CSSProperties, ReactNode } from "react";

/** Loading messages end with an ellipsis; errors and empty states do not. */
export function isLoadingMessage(message: string | null | undefined): message is string {
  return Boolean(message && message.trim().endsWith("…"));
}

type Vars = CSSProperties & { "--m": string; "--c"?: string; "--o"?: number; "--d"?: string };

/**
 * Each pitch line carries its own monogram destination (--m), monogram colour (--c),
 * monogram opacity (--o) and draw delay (--d). The lines draw in as a pitch, snap into
 * the FI monogram, hold, then unfold back into a pitch.
 */
const SEGMENTS: { at: string; d: string; vars: Vars }[] = [
  // Touchlines: top and bottom become the cap line and baseline; left and right the stems.
  { at: "30 22", d: "M0 0H240", vars: { "--m": "translate(58px,23px) scale(.5167,1)", "--c": "var(--line)" } },
  { at: "30 178", d: "M0 0H240", vars: { "--m": "translate(58px,-23px) scale(.5167,1)", "--c": "var(--line)" } },
  { at: "30 22", d: "M0 0V156", vars: { "--m": "translate(70px,23px) scale(1,.7051)" } },
  { at: "270 22", d: "M0 0V156", vars: { "--m": "translate(-70px,23px) scale(1,.7051)" } },
  // Halfway line is the I.
  { at: "150 22", d: "M0 0V156", vars: { "--m": "translate(36px,23px) scale(1,.7051)", "--d": ".06s" } },
  // Penalty boxes.
  { at: "30 53.9", d: "M0 0H37.7", vars: { "--m": "translate(70px,-8.9px) scale(1.7507,1)", "--d": ".12s" } },
  { at: "67.7 53.9", d: "M0 0V92.2", vars: { "--m": "translate(46.3px,52.1px) scale(1,.5315)", "--d": ".12s" } },
  { at: "30 146.1", d: "M0 0H37.7", vars: { "--m": "translate(70px,8.9px) scale(.3714,1)", "--d": ".12s" } },
  { at: "232.3 53.9", d: "M0 0H37.7", vars: { "--m": "translate(-46.3px,-8.9px) scale(.3714,1)", "--d": ".12s" } },
  { at: "232.3 53.9", d: "M0 0V92.2", vars: { "--m": "translate(-78.3px,38.1px) scale(1,.1518)", "--d": ".12s" } },
  { at: "232.3 146.1", d: "M0 0H37.7", vars: { "--m": "translate(-46.3px,8.9px) scale(.3714,1)", "--d": ".12s" } },
  // Six-yard boxes.
  { at: "30 79.1", d: "M0 0H12.6", vars: { "--m": "translate(84px,-20.1px) scale(4.127,1)", "--d": ".18s" } },
  { at: "42.6 79.1", d: "M0 0V41.8", vars: { "--m": "translate(71.4px,-20.1px) scale(1,.7895)", "--d": ".18s" } },
  { at: "30 120.9", d: "M0 0H12.6", vars: { "--m": "translate(84px,-14.9px) scale(3.1746,1)", "--d": ".18s" } },
  { at: "257.4 79.1", d: "M0 0H12.6", vars: { "--m": "translate(-143.4px,12.9px) scale(3.1746,1)", "--d": ".18s" } },
  { at: "257.4 79.1", d: "M0 0V41.8", vars: { "--m": "translate(-91.4px,-34.1px) scale(1,.3349)", "--d": ".18s" } },
  { at: "257.4 120.9", d: "M0 0H12.6", vars: { "--m": "translate(-71.4px,34.1px) scale(1.111,1)", "--o": 0, "--d": ".18s" } },
];

function LoaderMark({ width = 320 }: { width?: number }) {
  return (
    <svg
      className="loader-mark"
      width={width}
      height={(width * 200) / 300}
      viewBox="0 0 300 200"
      aria-hidden="true"
      focusable="false"
    >
      {SEGMENTS.map((segment, index) => (
        <g key={index} transform={`translate(${segment.at})`}>
          <path className="mono-seg" d={segment.d} pathLength={1} style={segment.vars} />
        </g>
      ))}
      {/* Centre circle becomes the counter under the arm of the F. */}
      <g transform="translate(150 100)">
        <circle
          className="mono-ring"
          r="20.9"
          pathLength={1}
          style={{ "--m": "translate(-10px,31px) scale(.7656)", "--d": ".06s" } as Vars}
        />
      </g>
      {/* Penalty spots converge on the centre of the counter. */}
      <g transform="translate(55.1 100)">
        <rect
          className="mono-spot"
          x="-1.5"
          y="-1.5"
          width="3"
          height="3"
          style={{ "--m": "translate(84.9px,31px) scale(1.667)", "--d": ".22s" } as Vars}
        />
      </g>
      <g transform="translate(244.9 100)">
        <rect
          className="mono-spot"
          x="-1.5"
          y="-1.5"
          width="3"
          height="3"
          style={{ "--m": "translate(-104.9px,31px) scale(1.667)", "--d": ".22s" } as Vars}
        />
      </g>
    </svg>
  );
}

/** Full content-area loader: covers everything to the right of the workspace sidebar. */
export function PageLoader({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="page-loader" role="status" aria-live="polite">
      <LoaderMark />
      <p className="page-loader-label">{label}</p>
      {children}
    </div>
  );
}

/** Same mark at section size, for content that loads in the background of a usable page. */
export function InlineLoader({ label }: { label: string }) {
  return (
    <div className="inline-loader" role="status" aria-live="polite">
      <LoaderMark width={120} />
      <span>{label}</span>
    </div>
  );
}

/** Renders a loading message as the page loader and anything else as a notice. */
export function StatusMessage({ message }: { message: string | null | undefined }) {
  if (!message) return null;
  if (isLoadingMessage(message)) return <PageLoader label={message} />;
  return <div className="notice">{message}</div>;
}
