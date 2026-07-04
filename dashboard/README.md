# PolyWave dashboard

A read-only Next.js dashboard for the PolyWave bot (see the repo root
`README.md`). It polls `/api/state`, a route handler that reads the JSON
snapshot the Python bot writes to `../data/state.json` on every tick.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:3000. Start the bot (`python main.py` from the repo
root) separately — the dashboard will start showing data as soon as it
writes its first snapshot.

## Configuration

- `STATE_FILE_PATH` — absolute or relative (to `dashboard/`) path to the
  state file. Defaults to `../data/state.json`, matching the bot's default
  `STATE_FILE_PATH=data/state.json`. Only needs to be set if you changed the
  bot's path or run the dashboard from a different working directory.

## Notes

- The dashboard never contacts Polymarket, Binance, or a wallet — it only
  reads the state file the bot already wrote. Safe to leave open in live
  mode.
- `npm run build` prints a Turbopack file-tracing warning about
  `src/app/api/state/route.ts` reading a path outside the project — this is
  informational only (it affects standalone/serverless output tracing, which
  this app doesn't use) and doesn't affect `next dev` or `next start`.
