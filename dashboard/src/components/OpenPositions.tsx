import type { OpenPosition } from "@/lib/types";
import { SignalBadge } from "./Badge";

export function OpenPositions({ positions }: { positions: OpenPosition[] }) {
  if (positions.length === 0) return null;

  return (
    <div className="rounded-lg border border-border-hairline bg-surface-1 p-4">
      <p className="text-sm text-text-secondary">Open positions</p>
      <ul className="mt-2 flex flex-col gap-2">
        {positions.map((position) => (
          <li key={position.condition_id} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <SignalBadge signal={position.outcome} />
              <span className="text-text-muted">{position.market_slug}</span>
            </div>
            <span className="tabular-nums text-text-primary">
              {position.size_usdc.toFixed(2)} USDC @ {position.entry_price.toFixed(3)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
