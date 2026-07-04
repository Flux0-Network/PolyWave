"use client";

import { useEffect, useState } from "react";
import type { MarketInfo, Signal } from "@/lib/types";
import { SignalBadge } from "./Badge";

interface MarketCardProps {
  market: MarketInfo | null;
  signal: Signal | null;
  momentumBps: number | null;
  updatedAt: string;
}

function formatCountdown(seconds: number): string {
  const clamped = Math.max(0, Math.round(seconds));
  const m = Math.floor(clamped / 60);
  const s = clamped % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function MarketCard({ market, signal, momentumBps, updatedAt }: MarketCardProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  if (!market) {
    return (
      <div className="rounded-lg border border-border-hairline bg-surface-1 p-4">
        <p className="text-sm text-text-secondary">Current market</p>
        <p className="mt-2 text-text-muted">No active market found.</p>
      </div>
    );
  }

  const elapsedSincePoll = (now - new Date(updatedAt).getTime()) / 1000;
  const secondsUntilClose = market.seconds_until_close - elapsedSincePoll;
  const secondsSinceStart = market.seconds_since_start + elapsedSincePoll;
  const progress = Math.min(1, Math.max(0, secondsSinceStart / (market.window_end - market.window_start)));

  return (
    <div className="rounded-lg border border-border-hairline bg-surface-1 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-text-secondary">Current market</p>
          <p className="mt-1 font-medium text-text-primary">{market.question}</p>
          <p className="mt-0.5 text-xs text-text-muted">{market.slug}</p>
        </div>
        <SignalBadge signal={signal} />
      </div>

      <div className="mt-4 flex items-center gap-4">
        <div className="flex-1">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-gridline">
            <div
              className="h-full rounded-full bg-[var(--series-blue)] transition-[width]"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-xs text-text-muted">
            <span>window open</span>
            <span>closes in {formatCountdown(secondsUntilClose)}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-6 text-sm">
        <div>
          <span className="text-text-secondary">Momentum </span>
          <span className="font-medium text-text-primary tabular-nums">
            {momentumBps === null ? "n/a" : `${momentumBps >= 0 ? "+" : ""}${momentumBps.toFixed(1)} bps`}
          </span>
        </div>
        <div>
          <span className="text-text-secondary">Accepting orders </span>
          <span className="font-medium text-text-primary">{market.accepting_orders ? "yes" : "no"}</span>
        </div>
      </div>
    </div>
  );
}
