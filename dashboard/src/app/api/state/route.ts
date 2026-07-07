import { promises as fs } from "fs";
import path from "path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// Must match polywave/state_store.py's SUPABASE_TABLE / SUPABASE_STATE_ROW_ID.
const SUPABASE_TABLE = "bot_state";
const SUPABASE_STATE_ROW_ID = "singleton";

// If the last push is older than this, treat state as stale (bot probably
// stopped) instead of showing a frozen snapshot forever.
const STATE_TTL_SECONDS = Number(process.env.STATE_TTL_SECONDS ?? 120);

// The Python bot writes its state snapshot to data/state.json at the repo
// root (STATE_FILE_PATH in polywave/config.py). The dashboard normally runs
// from ./dashboard, one level below, so default one directory up from there.
// This only works when the dashboard and bot share a filesystem (local dev,
// or both on the same server) -- on Vercel, SUPABASE_URL/SERVICE_ROLE_KEY
// are used instead, see below.
const STATE_FILE_PATH =
  process.env.STATE_FILE_PATH ?? path.join(/* turbopackIgnore: true */ process.cwd(), "..", "data", "state.json");

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

export async function GET() {
  if (SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY) {
    return readFromSupabase(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
  }
  return readFromFile();
}

async function readFromSupabase(url: string, key: string) {
  try {
    const res = await fetch(
      `${url}/rest/v1/${SUPABASE_TABLE}?id=eq.${SUPABASE_STATE_ROW_ID}&select=data,updated_at`,
      {
        headers: {
          apikey: key,
          Authorization: `Bearer ${key}`,
          Accept: "application/vnd.pgrst.object+json",
        },
        cache: "no-store",
      },
    );
    if (res.status === 406) {
      // PGRST116: no row yet (bot hasn't pushed anything).
      return NextResponse.json({ available: false });
    }
    if (!res.ok) {
      return NextResponse.json({ available: false, error: `Supabase request failed: ${res.status}` }, { status: 502 });
    }
    const row = (await res.json()) as { data: Record<string, unknown>; updated_at: string };
    const ageSeconds = (Date.now() - new Date(row.updated_at).getTime()) / 1000;
    if (ageSeconds > STATE_TTL_SECONDS) {
      return NextResponse.json({ available: false });
    }
    return NextResponse.json({ available: true, ...row.data });
  } catch (err: unknown) {
    return NextResponse.json(
      { available: false, error: err instanceof Error ? err.message : String(err) },
      { status: 500 },
    );
  }
}

async function readFromFile() {
  try {
    const raw = await fs.readFile(STATE_FILE_PATH, "utf-8");
    const state = JSON.parse(raw);
    return NextResponse.json({ available: true, ...state });
  } catch (err: unknown) {
    const code = (err as NodeJS.ErrnoException)?.code;
    if (code === "ENOENT") {
      return NextResponse.json({ available: false });
    }
    return NextResponse.json(
      { available: false, error: err instanceof Error ? err.message : String(err) },
      { status: 500 },
    );
  }
}
