function normalizePrefix(prefix: string): string {
  const trimmed = prefix.trim();
  if (!trimmed || trimmed === "/") return "";
  return trimmed.startsWith("/")
    ? trimmed.replace(/\/$/, "")
    : `/${trimmed.replace(/\/$/, "")}`;
}

export function getUrlPrefix(): string {
  const fromGlobal = (window as unknown as { __FLOWER_URL_PREFIX__?: string })
    .__FLOWER_URL_PREFIX__;
  if (typeof fromGlobal === "string") return normalizePrefix(fromGlobal);

  const meta = document.querySelector('meta[name="flower:url_prefix"]');
  const content = meta?.getAttribute("content");
  if (typeof content === "string") return normalizePrefix(content);

  return "";
}

export function joinWithPrefix(prefix: string, path: string): string {
  const normalizedPrefix = normalizePrefix(prefix);
  if (!path) return normalizedPrefix || "/";

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedPrefix}${normalizedPath}` || "/";
}
