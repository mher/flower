import { getUrlPrefix, joinWithPrefix } from "../lib/urlPrefix";

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
    throw new Error(text || `Request failed: ${res.status} ${res.statusText}`);
  }

  return (await res.json()) as T;
}
