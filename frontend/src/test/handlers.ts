import { http, HttpResponse } from "msw";

/** Credentials the default login handler accepts. */
export const TEST_USERNAME = "operator";
export const TEST_PASSWORD = "correct-horse-battery";

/** The bearer token the default login handler issues and default protected handlers require. */
export const TEST_ACCESS_TOKEN = "operator:1800000000:test-signature";

export const LOGIN_PATH = "/api/v1/auth/login";
export const PROTECTED_PING_PATH = "/api/v1/protected/ping";
export const READINESS_PATH = "/api/v1/ready";

/**
 * Default handlers.
 *
 * These mirror the accepted backend contract closely enough that the transport, the
 * bearer attachment, the `401` lifecycle and the readiness interpretation are all
 * exercised over a real (intercepted) network boundary.
 */
export const handlers = [
  http.post(LOGIN_PATH, async ({ request }) => {
    const body = (await request.json()) as { username?: string; password?: string };
    if (body.username !== TEST_USERNAME || body.password !== TEST_PASSWORD) {
      return HttpResponse.json({ detail: "invalid credentials" }, { status: 401 });
    }
    return HttpResponse.json({ access_token: TEST_ACCESS_TOKEN, token_type: "bearer" });
  }),

  http.get(PROTECTED_PING_PATH, ({ request }) => {
    if (request.headers.get("Authorization") !== `Bearer ${TEST_ACCESS_TOKEN}`) {
      return HttpResponse.json({ detail: "authentication required" }, { status: 401 });
    }
    return HttpResponse.json({ status: "authenticated" });
  }),

  http.get(READINESS_PATH, () =>
    HttpResponse.json({ ready: true, run_mode: "TEST", local_only: true, reasons: [] }),
  ),
];
