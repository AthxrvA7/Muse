// Low-level HTTP for the Muse API. The site is served by the same server, so every call is
// same-origin: the browser sends the login cookie itself and no CORS is involved.

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type ErrorBody = { detail?: unknown } | null;

/** Turns any error body the API sends into one readable sentence. */
export function errorMessage(status: number, body: ErrorBody): string {
  const detail = body?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail) && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  if (Array.isArray(detail) && detail.length > 0) {
    // FastAPI validation errors: [{ loc: ["body", "field"], msg: "..." }]
    const first = detail[0] as { loc?: unknown[]; msg?: string };
    const field = (first.loc ?? []).filter((part) => part !== "body").join(".");
    return field ? `${field}: ${first.msg}` : String(first.msg);
  }
  if (typeof detail === "string") return detail;
  if (status === 429) return "Too many requests. Wait a moment and try again.";
  if (status >= 500) return "Muse had a problem. Please try again.";
  return `Request failed (${status}).`;
}

export async function request<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method ?? "GET",
      headers: options.body === undefined ? undefined : { "Content-Type": "application/json" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(0, "Can't reach Muse. Check your connection and try again.");
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, errorMessage(response.status, data));
  return data as T;
}
