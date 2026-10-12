/**
 * HTTP access to the REI API.
 *
 * The browser calls same-origin `/api/...`; Next.js forwards those requests
 * to the API server (see `rewrites` in next.config.ts), so no API address or
 * CORS setup is needed in the browser.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const UNREACHABLE =
  "The REI API is not reachable. This page reconnects by itself as soon as it is back; " +
  "if it stays down, double-click start-rei.cmd in the project folder.";

/** Whether an error means the API could not be reached (down, restarting), not that it refused. */
export function isUnreachable(error: unknown): boolean {
  return error instanceof ApiError && (error.status === null || error.status >= 500) && error.message === UNREACHABLE;
}

/** How long to wait before trying an unreachable API again. */
export const RECONNECT_MS = 5000;

async function request(path: string, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetch(`/api${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch {
    return null;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response = await request(path, init);
  // A read can safely be repeated once, which rides out a dropped connection
  // between the proxy and the API.
  const isRead = !init?.method || init.method === "GET";
  if (isRead && (response === null || response.status >= 500)) {
    response = await request(path, init);
  }
  if (response === null) throw new ApiError(UNREACHABLE, null);

  if (!response.ok) {
    // FastAPI reports errors as {"detail": "..."}; the Next.js proxy answers
    // with a bare 5xx when the API server is down.
    const detail = await response
      .json()
      .then((body: { detail?: unknown }) => (typeof body.detail === "string" ? body.detail : null))
      .catch(() => null);
    if (detail) throw new ApiError(detail, response.status);
    if (response.status >= 500) throw new ApiError(UNREACHABLE, response.status);
    throw new ApiError(`The API request failed (${response.status}).`, response.status);
  }
  return (await response.json()) as T;
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
