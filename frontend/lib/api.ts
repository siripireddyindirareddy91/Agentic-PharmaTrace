export async function api(path: string, body?: unknown, method?: string) {
  const response = await fetch("/api/" + path, {
    method: method || (body ? "POST" : "GET"),
    headers:
      body instanceof FormData
        ? undefined
        : { "Content-Type": "application/json" },
    body:
      body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    let message = "Request failed";
    try {
      const d = await response.json();
      message =
        typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail);
    } catch {}
    throw new Error(message);
  }
  return response.json();
}
export type Row = Record<string, any>;
