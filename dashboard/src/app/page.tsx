"use client";

import { DryRunBadge } from "@/components/Badge";
import { MarketCard } from "@/components/MarketCard";
import { OpenPositions } from "@/components/OpenPositions";
import { PnlChart } from "@/components/PnlChart";
import { StatTile } from "@/components/StatTile";
import { TradesTable } from "@/components/TradesTable";
import { useBotState } from "@/lib/useBotState";

export default function Home() {
  const { data, lastFetchFailed } = useBotState();

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">PolyWave</h1>
          <p className="text-sm text-text-secondary">BTC 5-minute Polymarket bot</p>
        </div>
        {data?.available && <DryRunBadge dryRun={data.dry_run} />}
      </header>

      {lastFetchFailed && (
        <div className="rounded-lg border border-border-hairline bg-surface-1 p-3 text-sm text-status-critical">
          Couldn&apos;t reach the dashboard API. Retrying every 5s…
        </div>
      )}

      {!data && <div className="text-sm text-text-muted">Loading…</div>}

      {data && !data.available && (
        <div className="rounded-lg border border-border-hairline bg-surface-1 p-6 text-sm text-text-secondary">
          No state file found yet. Start the bot (<code className="text-text-primary">python main.py</code>) — it
          writes a snapshot on every tick, and this page will pick it up automatically.
          {data.error && <p className="mt-2 text-status-critical">{data.error}</p>}
        </div>
      )}

      {data?.available && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatTile
              label="Realized PnL (today)"
              value={`${data.stats.realized_pnl_usdc >= 0 ? "+" : ""}${data.stats.realized_pnl_usdc.toFixed(2)}`}
              deltaLabel="USDC"
              deltaTone={data.stats.realized_pnl_usdc >= 0 ? "good" : "critical"}
            />
            <StatTile
              label="Win rate (today)"
              value={data.stats.win_rate === null ? "n/a" : `${Math.round(data.stats.win_rate * 100)}%`}
              deltaLabel={`${data.stats.trades_won}W / ${data.stats.trades_lost}L`}
            />
            <StatTile label="Trades opened (today)" value={String(data.stats.trades_opened)} />
            <StatTile label="Open positions" value={String(data.stats.open_positions)} />
          </div>

          <MarketCard
            market={data.market}
            signal={data.signal}
            momentumBps={data.momentum_bps}
            updatedAt={data.updated_at}
          />

          <OpenPositions positions={data.open_positions} />

          <PnlChart trades={data.recent_trades} />

          <TradesTable trades={data.recent_trades} />

          <p className="text-center text-xs text-text-muted">
            Last updated {new Date(data.updated_at).toLocaleTimeString()}
          </p>
        </>
      )}
    </div>
  );
}
