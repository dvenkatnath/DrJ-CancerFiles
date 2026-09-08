import { useEffect, useRef, useState } from "react";

/** Runs `fn` immediately and then every `intervalMs`, storing the latest
 * resolved value. Used for lightweight badge counts (curation queue size,
 * pending-review counts) -- not a replacement for real-time push, but keeps
 * the sidebar reasonably fresh without adding a websocket layer. */
export function usePolling<T>(fn: () => Promise<T>, intervalMs: number, deps: unknown[] = []): T | undefined {
  const [value, setValue] = useState<T>();
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let cancelled = false;
    const tick = () => {
      fnRef.current()
        .then((v) => !cancelled && setValue(v))
        .catch(() => {
          /* keep last known value on transient errors */
        });
    };
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return value;
}
