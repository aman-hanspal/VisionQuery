"use client";

import { useEffect, useMemo, useState } from "react";
import { resolveClasses } from "@/lib/api";

const EMPTY: string[] = [];

export function useClasses(prompt: string) {
  const query = prompt.trim();
  const [attempt, setAttempt] = useState(0);
  const [resolved, setResolved] = useState<{
    query: string;
    attempt: number;
    classes: string[];
    error: string;
  } | null>(null);

  useEffect(() => {
    if (!query) return;
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const data = await resolveClasses(query, { signal: controller.signal });
        if (active)
          setResolved({ query, attempt, classes: data.classes, error: "" });
      } catch (error) {
        if (active)
          setResolved({
            query,
            attempt,
            classes: [],
            error: error instanceof Error ? error.message : String(error),
          });
      }
    }, 450);
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [query, attempt]);

  // Gate by exact query during render, including the render before effect cleanup.
  const current =
    resolved?.query === query && resolved.attempt === attempt ? resolved : null;
  const promptClasses = query ? (current?.classes ?? EMPTY) : EMPTY;
  const classesBusy = Boolean(query && !current);
  const displayClasses = useMemo(() => promptClasses, [promptClasses]);
  return {
    promptClasses,
    displayClasses,
    classesBusy,
    classesError: current?.error ?? "",
    retryClasses: () => setAttempt((value) => value + 1),
  };
}
