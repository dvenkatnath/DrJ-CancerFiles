import { ArrowDown, ArrowRight, ArrowUp, TrendingUp } from "lucide-react";
import type { TrendMarker } from "../types";
import { Badge } from "./ui";
import { openDocumentInNewTab } from "../hooks/useDocumentBlobUrl";

const DIRECTION_META: Record<TrendMarker["direction"], { label: string; tone: "success" | "warning" | "danger" | "neutral"; Icon: typeof ArrowUp }> = {
  // Direction alone isn't "good" or "bad" clinically (a rising Hemoglobin is
  // good, a rising CA-125 usually isn't) -- tone here is neutral/informational
  // on purpose; a clinician reads the number, this just says which way it moved.
  rising: { label: "Rising", tone: "warning", Icon: ArrowUp },
  falling: { label: "Falling", tone: "success", Icon: ArrowDown },
  stable: { label: "Stable", tone: "neutral", Icon: ArrowRight },
  insufficient_data: { label: "Single reading", tone: "neutral", Icon: ArrowRight },
};

function Sparkline({ marker }: { marker: TrendMarker }) {
  const w = 160;
  const h = 40;
  const pad = 4;
  const points = marker.points;
  if (points.length < 2) {
    return (
      <svg width={w} height={h} className="shrink-0">
        <line x1={pad} y1={h / 2} x2={w - pad} y2={h / 2} stroke="var(--color-border)" strokeWidth={1} />
        <circle cx={w - pad} cy={h / 2} r={3} fill="var(--color-accent)" />
      </svg>
    );
  }
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const coords = points.map((p, i) => {
    const x = pad + (i / (points.length - 1)) * (w - pad * 2);
    const y = h - pad - ((p.value - min) / range) * (h - pad * 2);
    return [x, y] as const;
  });
  const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [lastX, lastY] = coords[coords.length - 1];

  return (
    <svg width={w} height={h} className="shrink-0" role="img" aria-label={`${marker.test} trend over ${points.length} readings`}>
      <path d={path} fill="none" stroke="var(--color-accent)" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" />
      {coords.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === coords.length - 1 ? 3 : 2} fill="var(--color-accent)" opacity={i === coords.length - 1 ? 1 : 0.5} />
      ))}
      <circle cx={lastX} cy={lastY} r={5} fill="none" stroke="var(--color-accent)" strokeWidth={1} opacity={0.4} />
    </svg>
  );
}

function MarkerCard({ marker }: { marker: TrendMarker }) {
  const meta = DIRECTION_META[marker.direction];
  const first = marker.points[0];
  return (
    <div className="rounded-md border border-[var(--color-border)] p-3 flex items-center gap-3">
      <Sparkline marker={marker} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-sm font-semibold">{marker.test}</span>
          <Badge tone={meta.tone}>
            <meta.Icon size={11} /> {meta.label}
          </Badge>
        </div>
        <p className="text-sm mt-0.5">
          {marker.latest_value}
          {marker.unit ? ` ${marker.unit}` : ""}
          <span className="text-[var(--color-text-muted)]">
            {marker.latest_date ? ` on ${marker.latest_date}` : " (date unrecorded)"}
          </span>
        </p>
        {marker.points.length > 1 && (
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            {marker.points.length} readings since {first.date || "an undated result"} · tap a point's source below
          </p>
        )}
        {marker.points.length > 1 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {marker.points.map((p, i) => (
              <button
                key={p.fact_id || i}
                onClick={() => p.document_id && openDocumentInNewTab(p.document_id)}
                disabled={!p.document_id}
                className="text-[11px] rounded border border-[var(--color-border)] px-1.5 py-0.5 text-[var(--color-text-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] disabled:opacity-50 disabled:hover:border-[var(--color-border)] disabled:hover:text-[var(--color-text-muted)]"
                title={p.document_id ? "Open source document" : "Source document unavailable"}
              >
                {p.value}
                {p.date ? ` · ${p.date}` : ""}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** Per-lab-marker trend charts (CA-125, Hemoglobin, CEA, ...), aggregated
 * server-side from every published lab_highlights fact across the patient's
 * whole record -- GET /patients/{id}/wiki/trends (app/services/trends.py).
 * Renders nothing when there's no structured lab data yet (a brand-new
 * patient, or one whose lab facts haven't been curator-accepted). */
export function LabTrends({ markers }: { markers: TrendMarker[] }) {
  if (markers.length === 0) return null;
  return (
    <section className="bg-white border border-[var(--color-border)] rounded-lg p-4">
      <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-3 flex items-center gap-1">
        <TrendingUp size={12} /> Lab trends
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {markers.map((m) => (
          <MarkerCard key={m.test} marker={m} />
        ))}
      </div>
    </section>
  );
}
