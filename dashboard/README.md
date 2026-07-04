# PolyWave dashboard

A read-only Next.js dashboard for the PolyWave bot (see the repo root
`README.md`). It polls `/api/state`, a route handler that reads the bot's
JSON state snapshot either from a local file or from a remote KV store.

## Run locally (bot on the same machine)

```bash
npm install
npm run dev
```

Open http://localhost:3000. Start the bot (`python main.py` from the repo
root) separately — the dashboard reads `../data/state.json`, which the bot
writes on every tick.

## Deploy to Vercel (bot running elsewhere)

Vercel functions can't read a file on your bot's machine, so in production
`/api/state` reads from an Upstash-compatible REST KV store that the bot
pushes to instead. See the "Deploying the dashboard to Vercel" section in
the repo root `README.md` for the full setup. Short version: set
`KV_REST_API_URL` and `KV_REST_API_TOKEN` to the same values on both the
bot's `.env` and this Vercel project, and set the project's **Root
Directory** to `dashboard`.

## Configuration

- `KV_REST_API_URL` / `KV_REST_API_TOKEN` — when both are set, state is read
  from this REST KV store instead of the local file. Required on Vercel;
  optional locally (see `.env.local.example`).
- `STATE_FILE_PATH` — only used when the KV vars above are unset. Absolute
  or relative (to `dashboard/`) path to the state file. Defaults to
  `../data/state.json`, matching the bot's default `STATE_FILE_PATH`.

## Notes

- The dashboard never contacts Polymarket, Binance, or a wallet — it only
  reads state the bot already wrote (from a file or from KV). Safe to leave
  open in live mode.
- `npm run build` prints a Turbopack file-tracing warning about
  `src/app/api/state/route.ts`'s local-file fallback reading a path outside
  the project. It's informational — the route still works correctly on
  Vercel (which uses the KV path, not the file path) and under `next dev`
  / `next start`.
