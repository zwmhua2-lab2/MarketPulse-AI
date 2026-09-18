import createClient from "openapi-fetch";

import type { paths } from "./generated";

export type { paths };

/**
 * Endpoints whose `401` means "the credentials in this request were rejected", never
 * "the bearer session is no longer valid".
 *
 * This is the frozen public read surface plus the login endpoint (UI-V1-D01 §26).
 * A `401` anywhere else is an authoritative statement about the session.
 */
const PUBLIC_ENDPOINTS: readonly string[] = [
  "/api/v1/auth/login",
  "/api/v1/live",
  "/api/v1/ready",
  "/api/v1/health",
];

export interface ApiTransportOptions {
  /** The current bearer access token, or `null` when there is no session. */
  readonly getToken: () => string | null;
  /** The local-only identity for the current Auth Session Boundary lifetime. */
  readonly getSessionGeneration: () => symbol;
  /** Whether the Provider lifetime which owns this client is still mounted. */
  readonly getProviderActive?: () => boolean;
  /** Called when the backend says the bearer session is no longer valid. */
  readonly onUnauthorized: () => void;
}

function isProtectedRequest(request: Request): boolean {
  return !PUBLIC_ENDPOINTS.includes(new URL(request.url).pathname);
}

/**
 * The MarketPulse API transport.
 *
 * Application code targets the generated `paths` — `/api/v1/...` — and never
 * hard-codes a backend host. The generated path is resolved against the current
 * document origin so the request stays same-origin and same-scheme; in development
 * the Vite `/api` proxy forwards it to `127.0.0.1:8000` (see `vite.config.ts`).
 *
 * The origin is supplied explicitly rather than left empty because the Fetch
 * `Request` constructor rejects a relative URL outside a browser document context —
 * which is the environment the transport is tested in.
 *
 * Responsibilities are deliberately narrow: bearer attachment and the `401`
 * lifecycle. Error classification lives in `errors.ts`; readiness semantics live in
 * `readiness.ts`.
 */
export function createApiClient(options: ApiTransportOptions) {
  const client = createClient<paths>({ baseUrl: window.location.origin });
  // `id` is unique for one openapi-fetch lifecycle. This ownership map is deliberately
  // local to this client: it is never serialized, persisted, or attached to a request.
  const requestSessionGenerations = new Map<string, symbol>();

  client.use({
    onRequest({ request, id }) {
      if (isProtectedRequest(request)) {
        // Capture at actual dispatch. Later session transitions must not change this
        // request's ownership.
        requestSessionGenerations.set(id, options.getSessionGeneration());
      }

      const token = options.getToken();
      if (token !== null && token !== "") {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
      return request;
    },
    onResponse({ request, response, id }) {
      const requestSessionGeneration = requestSessionGenerations.get(id);
      requestSessionGenerations.delete(id);

      if (
        response.status === 401 &&
        isProtectedRequest(request) &&
        requestSessionGeneration !== undefined &&
        requestSessionGeneration === options.getSessionGeneration() &&
        (options.getProviderActive?.() ?? true)
      ) {
        options.onUnauthorized();
      }
      return response;
    },
    onError({ id }) {
      requestSessionGenerations.delete(id);
    },
  });

  return client;
}

export type ApiClient = ReturnType<typeof createApiClient>;
