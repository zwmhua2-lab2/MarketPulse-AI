import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { LOGIN_PATH, PROTECTED_PING_PATH, TEST_ACCESS_TOKEN } from "../test/handlers";
import { server } from "../test/server";
import { createApiClient } from "./client";
import { HttpError, NetworkError, UnauthorizedError, UnexpectedResponse } from "./errors";
import { READINESS_PATH, readReadiness } from "./readiness";
import { requestData } from "./transport";

/** A protected endpoint that is not `/ready`, used for the generic transport cases. */
const RUNTIME_PATH = "/api/v1/runtime";

function client(onUnauthorized: () => void = () => undefined, token: string | null = null) {
  return createApiClient({ getToken: () => token, onUnauthorized });
}

describe("transport error classification", () => {
  it("classifies a network failure as NetworkError", async () => {
    server.use(http.get(READINESS_PATH, () => HttpResponse.error()));

    await expect(readReadiness(client())).rejects.toBeInstanceOf(NetworkError);
  });

  it("classifies an ordinary 5xx as HttpError and retains the status", async () => {
    server.use(
      http.get(READINESS_PATH, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    );

    const failure = await readReadiness(client()).catch((cause: unknown) => cause);

    expect(failure).toBeInstanceOf(HttpError);
    expect((failure as HttpError).status).toBe(500);
    expect(failure).not.toBeInstanceOf(NetworkError);
  });

  it("classifies an ordinary 4xx as HttpError and retains the status", async () => {
    server.use(
      http.get(READINESS_PATH, () => HttpResponse.json({ detail: "not found" }, { status: 404 })),
    );

    const failure = await readReadiness(client()).catch((cause: unknown) => cause);

    expect(failure).toBeInstanceOf(HttpError);
    expect((failure as HttpError).status).toBe(404);
  });

  it("keeps 401 distinct from other HTTP failures", async () => {
    server.use(
      http.get(READINESS_PATH, () =>
        HttpResponse.json({ detail: "authentication required" }, { status: 401 }),
      ),
    );

    const failure = await readReadiness(client()).catch((cause: unknown) => cause);

    expect(failure).toBeInstanceOf(UnauthorizedError);
    expect(failure).not.toBeInstanceOf(HttpError);
    expect((failure as UnauthorizedError).status).toBe(401);
  });

  it("targets a same-origin relative path and never a hard-coded backend host", async () => {
    const urls: string[] = [];
    server.use(
      http.get(READINESS_PATH, ({ request }) => {
        urls.push(request.url);
        return HttpResponse.json({ ready: true, reasons: [] });
      }),
    );

    await readReadiness(client());

    expect(urls).toHaveLength(1);
    const url = new URL(urls[0] as string);
    expect(url.origin).toBe(window.location.origin);
    expect(url.pathname).toBe(READINESS_PATH);
    expect(urls[0]).not.toContain("127.0.0.1:8000");
  });

  it("attaches the bearer token it is given, and none when unauthenticated", async () => {
    const seen: Array<string | null> = [];
    server.use(
      http.get(PROTECTED_PING_PATH, ({ request }) => {
        seen.push(request.headers.get("Authorization"));
        return HttpResponse.json({ status: "authenticated" });
      }),
    );

    await client().GET(PROTECTED_PING_PATH);
    await client(() => undefined, TEST_ACCESS_TOKEN).GET(PROTECTED_PING_PATH);

    expect(seen).toEqual([null, `Bearer ${TEST_ACCESS_TOKEN}`]);
  });
});

describe("401 lifecycle ownership", () => {
  it("does not invalidate the session on a login 401", async () => {
    const invalidations: number[] = [];
    server.use(
      http.post(LOGIN_PATH, () =>
        HttpResponse.json({ detail: "invalid credentials" }, { status: 401 }),
      ),
    );

    await client(() => invalidations.push(1), "stale-token").POST(LOGIN_PATH, {
      body: { username: "operator", password: "wrong" },
    });

    expect(invalidations).toHaveLength(0);
  });

  it("invalidates the session on a 401 from a protected endpoint", async () => {
    const invalidations: number[] = [];
    server.use(
      http.get(PROTECTED_PING_PATH, () =>
        HttpResponse.json({ detail: "invalid session" }, { status: 401 }),
      ),
    );

    await client(() => invalidations.push(1), "stale-token").GET(PROTECTED_PING_PATH);

    expect(invalidations).toHaveLength(1);
  });

  it("does not invalidate the session on a 503 readiness response", async () => {
    const invalidations: number[] = [];
    server.use(
      http.get(READINESS_PATH, () =>
        HttpResponse.json({ ready: false, reasons: ["NOT_READY"] }, { status: 503 }),
      ),
    );

    await readReadiness(client(() => invalidations.push(1), "stale-token"));

    expect(invalidations).toHaveLength(0);
  });
});

/**
 * The generic boundary every non-`/ready` caller uses.
 *
 * These cases deliberately avoid `/ready`: the point is that a Product Query module can
 * get one normalized transport failure without reproducing the checks itself, and that
 * the authoritative `/ready` `503` payload stays confined to `/ready`.
 */
describe("generic transport interpretation", () => {
  it("returns the typed success body instead of an outcome to unwrap", async () => {
    server.use(
      http.get(PROTECTED_PING_PATH, () => HttpResponse.json({ status: "authenticated" })),
    );

    const data = await requestData(() => client().GET(PROTECTED_PING_PATH));

    // The annotation is the assertion: `data` is the generated success body type, so the
    // caller never inspects `response.ok` and never reads `{ data, error, response }`.
    const status: string = data["status"];
    expect(status).toBe("authenticated");
  });

  it("classifies a network failure as NetworkError", async () => {
    server.use(http.get(PROTECTED_PING_PATH, () => HttpResponse.error()));

    const failure = await requestData(() => client().GET(PROTECTED_PING_PATH)).catch(
      (cause: unknown) => cause,
    );

    expect(failure).toBeInstanceOf(NetworkError);
    expect(failure).not.toBeInstanceOf(HttpError);
    expect(failure).not.toBeInstanceOf(UnauthorizedError);
  });

  it("classifies a 401 as UnauthorizedError without losing the session lifecycle", async () => {
    const invalidations: number[] = [];
    server.use(
      http.get(PROTECTED_PING_PATH, () =>
        HttpResponse.json({ detail: "invalid session" }, { status: 401 }),
      ),
    );

    const failure = await requestData(() =>
      client(() => invalidations.push(1), "stale-token").GET(PROTECTED_PING_PATH),
    ).catch((cause: unknown) => cause);

    expect(failure).toBeInstanceOf(UnauthorizedError);
    expect(failure).not.toBeInstanceOf(HttpError);
    expect((failure as UnauthorizedError).status).toBe(401);
    expect(invalidations).toHaveLength(1);
  });

  it("classifies an ordinary 4xx as HttpError and preserves the status and the error body", async () => {
    const body = { detail: "telemetry not found" };
    server.use(
      http.get(PROTECTED_PING_PATH, () => HttpResponse.json(body, { status: 404 })),
    );

    const failure = await requestData(() => client().GET(PROTECTED_PING_PATH)).catch(
      (cause: unknown) => cause,
    );

    expect(failure).toBeInstanceOf(HttpError);
    expect((failure as HttpError).status).toBe(404);
    expect((failure as HttpError).body).toEqual(body);
  });

  it("classifies an ordinary 5xx as HttpError and preserves a non-JSON error body", async () => {
    server.use(
      http.get(PROTECTED_PING_PATH, () =>
        HttpResponse.text("upstream unavailable", { status: 502 }),
      ),
    );

    const failure = await requestData(() => client().GET(PROTECTED_PING_PATH)).catch(
      (cause: unknown) => cause,
    );

    expect(failure).toBeInstanceOf(HttpError);
    expect((failure as HttpError).status).toBe(502);
    expect((failure as HttpError).body).toBe("upstream unavailable");
  });

  it("keeps the authoritative 503 payload confined to /ready", async () => {
    const payload = { ready: false, reasons: ["NOT_READY"] };
    server.use(http.get(RUNTIME_PATH, () => HttpResponse.json(payload, { status: 503 })));

    const failure = await requestData(() => client().GET(RUNTIME_PATH)).catch(
      (cause: unknown) => cause,
    );

    // Anywhere else a 503 is an ordinary 5xx failure — never a readiness verdict.
    expect(failure).toBeInstanceOf(HttpError);
    expect((failure as HttpError).status).toBe(503);
    expect((failure as HttpError).body).toEqual(payload);
    expect(failure).not.toBeInstanceOf(NetworkError);
    expect(failure).not.toBeInstanceOf(UnauthorizedError);
  });

  it("reports an uninterpretable 2xx body as UnexpectedResponse, not as a network failure", async () => {
    server.use(
      http.get(PROTECTED_PING_PATH, () =>
        HttpResponse.text("<html>proxy error</html>", {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    const failure = await requestData(() => client().GET(PROTECTED_PING_PATH)).catch(
      (cause: unknown) => cause,
    );

    expect(failure).toBeInstanceOf(UnexpectedResponse);
    expect(failure).not.toBeInstanceOf(NetworkError);
    expect(failure).not.toBeInstanceOf(HttpError);
    expect(failure).not.toBeInstanceOf(UnauthorizedError);
  });
});
