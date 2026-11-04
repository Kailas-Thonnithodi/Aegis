import { useEffect, useState } from "react";

export interface Polled<T> {
  data: T | undefined;
  failed: boolean;
  refresh: () => void;
}

export function usePolling<T>(
  load: () => Promise<T>,
  intervalMs: number | null,
): Polled<T> {
  const [data, setData] = useState<T>();
  const [failed, setFailed] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    const fetchNow = () => {
      load()
        .then((value) => {
          if (active) {
            setData(value);
            setFailed(false);
          }
        })
        .catch(() => {
          if (active) setFailed(true);
        });
    };
    fetchNow();
    const timer =
      intervalMs === null ? undefined : setInterval(fetchNow, intervalMs);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [load, intervalMs, tick]);

  return {
    data,
    failed,
    refresh: () => {
      setTick((value) => value + 1);
    },
  };
}

export function useHash(): string {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
    };
  }, []);

  return hash;
}
