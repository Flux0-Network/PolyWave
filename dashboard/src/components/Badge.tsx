import type { Signal } from "@/lib/types";

export function SignalBadge({ signal }: { signal: Signal | null }) {
  if (!signal) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-border-hairline px-2.5 py-0.5 text-sm text-text-muted">
        n/a
      </span>
    );
  }
  if (signal === "Skip") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-border-hairline px-2.5 py-0.5 text-sm text-text-secondary">
        <span aria-hidden>–</span> Skip
      </span>
    );
  }
  const isUp = signal === "Up";
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-medium"
      style={{
        color: isUp ? "var(--series-blue)" : "var(--series-red)",
        borderColor: isUp ? "var(--series-blue)" : "var(--series-red)",
      }}
    >
      <span aria-hidden>{isUp ? "▲" : "▼"}</span> {signal}
    </span>
  );
}

export function OutcomeBadge({ won }: { won: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-sm font-medium text-white"
      style={{ backgroundColor: won ? "var(--status-good)" : "var(--status-critical)" }}
    >
      <span aria-hidden>{won ? "✓" : "✕"}</span> {won ? "Won" : "Lost"}
    </span>
  );
}

export function DryRunBadge({ dryRun }: { dryRun: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-sm font-medium"
      style={{
        backgroundColor: dryRun ? "var(--status-warning)" : "var(--status-good)",
        color: dryRun ? "#3d2c00" : "white",
      }}
    >
      {dryRun ? "Dry run" : "Live"}
    </span>
  );
}
