"use client";

import { useMemo, useRef, useState } from "react";
import type { TradeRecord } from "@/lib/types";

interface PnlChartProps {
  trades: TradeRecord[]; // most-recent-first, as returned by the API
}

const WIDTH = 600;
const HEIGHT = 220;
const PAD = { top: 16, right: 16, bottom: 20, left: 48 };

function formatUsdc(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function PnlChart({ trades }: PnlChartProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const chronological = useMemo(() => [...trades].reverse(), [trades]);

  const points = useMemo(
    () =>
      chronological.reduce<{ trade: TradeRecord; cumulative: number }[]>((acc, trade) => {
        const previous = acc.length > 0 ? acc[acc.length - 1].cumulative : 0;
        acc.push({ trade, cumulative: previous + trade.pnl_usdc });
        return acc;
      }, []),
    [chronological],
  );

  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-border-hairline bg-surface-1 p-4">
        <p className="text-sm text-text-secondary">Cumulative PnL</p>
        <div className="flex h-48 items-center justify-center text-sm text-text-muted">
          No settled trades yet.
        </div>
      </div>
    );
  }

  const values = points.map((p) => p.cumulative);
  const rawMax = Math.max(0, ...values);
  const rawMin = Math.min(0, ...values);
  const spread = rawMax - rawMin || 1;
  const yMax = rawMax + spread * 0.15;
  const yMin = rawMin - spread * 0.15;

  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;

  const xFor = (i: number) => PAD.left + (points.length === 1 ? plotW / 2 : (i / (points.length - 1)) * plotW);
  const yFor = (v: number) => PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(p.cumulative)}`).join(" ");
  const areaPath = `${linePath} L ${xFor(points.length - 1)} ${yFor(0)} L ${xFor(0)} ${yFor(0)} Z`;

  const final = values[values.length - 1];
  const tone = final >= 0 ? "var(--status-good)" : "var(--status-critical)";
  const zeroY = yFor(0);

  function handlePointerMove(e: React.PointerEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const viewBoxX = ((e.clientX - rect.left) / rect.width) * WIDTH;
    const idx = Math.round(((viewBoxX - PAD.left) / plotW) * (points.length - 1));
    setHoverIndex(Math.min(points.length - 1, Math.max(0, idx)));
  }

  const hovered = hoverIndex !== null ? points[hoverIndex] : null;

  return (
    <div className="rounded-lg border border-border-hairline bg-surface-1 p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-sm text-text-secondary">Cumulative PnL</p>
        <p className="text-sm font-medium tabular-nums" style={{ color: tone }}>
          {formatUsdc(final)} USDC
        </p>
      </div>

      <div className="relative mt-2 h-56 w-full">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="h-full w-full"
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setHoverIndex(null)}
        >
          {/* y-axis reference labels */}
          <text x={4} y={PAD.top + 4} className="fill-text-muted text-[10px] tabular-nums">
            {yMax.toFixed(1)}
          </text>
          <text x={4} y={HEIGHT - PAD.bottom} className="fill-text-muted text-[10px] tabular-nums">
            {yMin.toFixed(1)}
          </text>

          {/* zero baseline */}
          <line x1={PAD.left} y1={zeroY} x2={WIDTH - PAD.right} y2={zeroY} stroke="var(--baseline)" strokeWidth={1} />
          <text x={4} y={zeroY + 3} className="fill-text-muted text-[10px] tabular-nums">
            0
          </text>

          {/* area wash */}
          <path d={areaPath} fill={tone} opacity={0.1} />

          {/* line */}
          <path d={linePath} fill="none" stroke={tone} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

          {/* end marker */}
          <circle cx={xFor(points.length - 1)} cy={yFor(final)} r={4} fill={tone} stroke="var(--surface-1)" strokeWidth={2} />

          {/* crosshair */}
          {hovered && hoverIndex !== null && (
            <>
              <line
                x1={xFor(hoverIndex)}
                y1={PAD.top}
                x2={xFor(hoverIndex)}
                y2={HEIGHT - PAD.bottom}
                stroke="var(--gridline)"
                strokeWidth={1}
              />
              <circle
                cx={xFor(hoverIndex)}
                cy={yFor(hovered.cumulative)}
                r={4}
                fill={tone}
                stroke="var(--surface-1)"
                strokeWidth={2}
              />
            </>
          )}
        </svg>

        {hovered && (
          <div
            className="pointer-events-none absolute top-0 rounded-md border border-border-hairline bg-surface-1 px-2.5 py-1.5 text-xs shadow-sm"
            style={{
              left: `${(hoverIndex! / Math.max(1, points.length - 1)) * 100}%`,
              transform: `translateX(${hoverIndex === 0 ? "0%" : hoverIndex === points.length - 1 ? "-100%" : "-50%"})`,
            }}
          >
            <p className="font-semibold tabular-nums text-text-primary">{formatUsdc(hovered.cumulative)} USDC</p>
            <p className="text-text-secondary">{formatTime(hovered.trade.settled_at)}</p>
            <p className="text-text-muted">
              {hovered.trade.outcome} · {hovered.trade.won ? "won" : "lost"} · trade {formatUsdc(hovered.trade.pnl_usdc)}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
