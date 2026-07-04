"use client";

import { useEffect, useRef, useState } from "react";
import type { StateResponse } from "./types";

const POLL_MS = 5000;

export function useBotState() {
  const [data, setData] = useState<StateResponse | null>(null);
  const [lastFetchFailed, setLastFetchFailed] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch("/api/state", { cache: "no-store" });
        const body: StateResponse = await res.json();
        if (!cancelled) {
          setData(body);
          setLastFetchFailed(false);
        }
      } catch {
        if (!cancelled) setLastFetchFailed(true);
      } finally {
        if (!cancelled) timer.current = setTimeout(poll, POLL_MS);
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  return { data, lastFetchFailed };
}
