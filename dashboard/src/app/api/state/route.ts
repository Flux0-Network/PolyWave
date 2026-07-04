import { promises as fs } from "fs";
import path from "path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// Must match polywave/state_store.py's KV_STATE_KEY.
const KV_STATE_KEY = "polywave:state";

// The Python bot writes its state snapshot to data/state.json at the repo
// root (STATE_FILE_PATH in polywave/config.py). The dashboard normally runs
// from ./dashboard, one level below, so default one directory up from there.
// This only works when the dashboard and bot share a filesystem (local dev,
// or both on the same server) -- on Vercel, KV_REST_API_URL/TOKEN are used
// instead, see below.
const STATE_FILE_PATH =
  process.env.STATE_FILE_PATH ?? path.join(/* turbopackIgnore: true */ process.cwd(), "..", "data", "state.json");

const KV_REST_API_URL = process.env.KV_REST_API_URL;
const KV_REST_API_TOKEN = process.env.KV_REST_API_TOKEN;

export async function GET() {
  if (KV_REST_API_URL && KV_REST_API_TOKEN) {
    return readFromKv(KV_REST_API_URL, KV_REST_API_TOKEN);
  }
  return readFromFile();
}

async function readFromKv(url: string, token: string) {
  try {
    const res = await fetch(`${url}/get/${KV_STATE_KEY}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ available: false, error: `KV request failed: ${res.status}` }, { status: 502 });
    }
    const body = (await res.json()) as { result: string | null };
    if (!body.result) {
      return NextResponse.json({ available: false });
    }
    const state = JSON.parse(body.result);
    return NextResponse.json({ available: true, ...state });
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
