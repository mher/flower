import { getUrlPrefix, joinWithPrefix } from "../lib/urlPrefix";

type ApiInFlightListener = () => void;

let apiInFlightCount = 0;
const apiInFlightListeners = new Set<ApiInFlightListener>();

function emitApiInFlightChange(): void {
  for (const listener of apiInFlightListeners) listener();
}

export function getApiInFlightCount(): number {
  return apiInFlightCount;
}

export function subscribeApiInFlight(
  listener: ApiInFlightListener
): () => void {
  apiInFlightListeners.add(listener);
  return () => {
    apiInFlightListeners.delete(listener);
  };
}

export type ApiQuery = Record<
  string,
  string | number | boolean | undefined | null
>;

export function buildApiUrl(
  path: string,
  query?: ApiQuery,
  urlPrefix?: string
): string {
  const prefix = urlPrefix ?? getUrlPrefix();
  const base = joinWithPrefix(prefix, path);
  if (!query) return base;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }

  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

export async function fetchJson<T>(
  url: string,
  signal?: AbortSignal
): Promise<T> {
  apiInFlightCount += 1;
  emitApiInFlightChange();

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
      signal,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(
        text || `Request failed: ${res.status} ${res.statusText}`
      );
    }

    return (await res.json()) as T;
  } finally {
    apiInFlightCount = Math.max(0, apiInFlightCount - 1);
    emitApiInFlightChange();
  }
}
