import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

export function refreshAll() {
  window.dispatchEvent(new CustomEvent("lm:refresh"));
}

export function useFetch(path, { auto = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(auto);

  const reload = useCallback(async () => {
    if (!path) return;
    try {
      const { data } = await api.get(path);
      setData(data);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("fetch failed", path, e?.message);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    if (auto) reload();
    const h = () => reload();
    window.addEventListener("lm:refresh", h);
    return () => window.removeEventListener("lm:refresh", h);
  }, [reload, auto]);

  return { data, loading, reload, setData };
}
