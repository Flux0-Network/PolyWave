import { promises as fs } from "fs";
import path from "path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// The Python bot writes its state snapshot to data/state.json at the repo
// root (STATE_FILE_PATH in polywave/config.py). The dashboard normally runs
// from ./dashboard, one level below, so default one directory up from there.
const STATE_FILE_PATH =
  process.env.STATE_FILE_PATH ?? path.join(/* turbopackIgnore: true */ process.cwd(), "..", "data", "state.json");

export async function GET() {
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
