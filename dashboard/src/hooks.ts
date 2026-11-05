import { useEffect, useState } from "react";

export interface Polled<T> {
  data: T | undefined;
  failed: boolean;
  refresh: () => void;
}

const always = () => true;

export function usePolling<T>(
  load: () => Promise<T>,
  intervalMs: number | null,
  keepPolling: (data: T) => boolean = always,
): Polled<T> {
  const [data, setData] = useState<T>();
  const [failed, setFailed] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setInterval> | undefined;
    const fetchNow = () => {
      load()
        .then((value) => {
          if (active) {
            setData(value);
            setFailed(false);
            if (!keepPolling(value)) clearInterval(timer);
          }
        })
        .catch(() => {
          if (active) setFailed(true);
        });
    };
    if (intervalMs !== null) timer = setInterval(fetchNow, intervalMs);
    fetchNow();
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [load, intervalMs, keepPolling, tick]);

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
