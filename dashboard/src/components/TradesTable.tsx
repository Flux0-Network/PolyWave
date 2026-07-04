import type { TradeRecord } from "@/lib/types";
import { OutcomeBadge, SignalBadge } from "./Badge";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function TradesTable({ trades }: { trades: TradeRecord[] }) {
  return (
    <div className="rounded-lg border border-border-hairline bg-surface-1 p-4">
      <p className="text-sm text-text-secondary">Recent trades</p>
      {trades.length === 0 ? (
        <div className="flex h-24 items-center justify-center text-sm text-text-muted">No settled trades yet.</div>
      ) : (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border-hairline text-text-muted">
                <th className="py-2 pr-4 font-medium">Settled</th>
                <th className="py-2 pr-4 font-medium">Market</th>
                <th className="py-2 pr-4 font-medium">Side</th>
                <th className="py-2 pr-4 font-medium">Entry</th>
                <th className="py-2 pr-4 font-medium">Size</th>
                <th className="py-2 pr-4 font-medium">Result</th>
                <th className="py-2 pr-0 text-right font-medium">PnL</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.condition_id} className="border-b border-border-hairline last:border-0">
                  <td className="py-2 pr-4 text-text-secondary tabular-nums">{formatTime(trade.settled_at)}</td>
                  <td className="py-2 pr-4 text-text-muted">{trade.market_slug}</td>
                  <td className="py-2 pr-4">
                    <SignalBadge signal={trade.outcome} />
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-text-primary">{trade.entry_price.toFixed(3)}</td>
                  <td className="py-2 pr-4 tabular-nums text-text-primary">{trade.size_usdc.toFixed(2)}</td>
                  <td className="py-2 pr-4">
                    <OutcomeBadge won={trade.won} />
                  </td>
                  <td
                    className="py-2 pr-0 text-right font-medium tabular-nums"
                    style={{ color: trade.pnl_usdc >= 0 ? "var(--delta-good)" : "var(--status-critical)" }}
                  >
                    {trade.pnl_usdc >= 0 ? "+" : ""}
                    {trade.pnl_usdc.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
