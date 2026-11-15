import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Runs `fetcher()` whenever `deps` change and exposes { data, loading, error, reload }.
 * Optional `pollMs` re-fetches quietly in the background (no loading spinner) - used for order tracking.
 * Stale responses (from an older request) are ignored.
 */
export function useFetch(fetcher, deps = [], { pollMs = 0 } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const requestId = useRef(0);

  const run = useCallback(async (silent) => {
    const id = ++requestId.current;
    if (!silent) {
      setLoading(true);
      setError('');
    }
    try {
      const result = await fetcherRef.current();
      if (id === requestId.current) {
        setData(result);
        setError('');
      }
    } catch (err) {
      if (id === requestId.current && !silent) setError(err.message);
    } finally {
      if (id === requestId.current && !silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    run(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (!pollMs) return undefined;
    const timer = setInterval(() => run(true), pollMs);
    return () => clearInterval(timer);
  }, [pollMs, run]);

  const reload = useCallback((silent = true) => run(silent), [run]);
  return { data, loading, error, reload, setData };
}

/** Small helper for "click button -> call API -> show error" flows. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const run = useCallback(async (fn) => {
    setBusy(true);
    setError('');
    try {
      return await fn();
    } catch (err) {
      setError(err.message);
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, error, setError, run };
}
