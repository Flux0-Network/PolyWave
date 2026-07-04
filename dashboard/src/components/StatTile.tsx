interface StatTileProps {
  label: string;
  value: string;
  deltaLabel?: string;
  deltaTone?: "good" | "critical" | "neutral";
}

export function StatTile({ label, value, deltaLabel, deltaTone = "neutral" }: StatTileProps) {
  const deltaColor =
    deltaTone === "good"
      ? "text-delta-good"
      : deltaTone === "critical"
        ? "text-status-critical"
        : "text-text-secondary";

  return (
    <div className="rounded-lg border border-border-hairline bg-surface-1 p-4">
      <p className="text-sm text-text-secondary">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-text-primary">{value}</p>
      {deltaLabel && <p className={`mt-1 text-sm ${deltaColor}`}>{deltaLabel}</p>}
    </div>
  );
}
