import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { createQueryClient } from "../app/queryClient";
import { server } from "../test/server";
import { createApiClient } from "./client";
import { HttpError, NetworkError, UnauthorizedError, UnexpectedResponse } from "./errors";
import { READINESS_PATH, readReadiness, type ReadinessPayload } from "./readiness";

function readinessClient() {
  return createApiClient({ getToken: () => null, onUnauthorized: () => undefined });
}

function readinessPayload(overrides: Partial<ReadinessPayload> = {}): ReadinessPayload {
  return {
    ready: true,
    status: "READY",
    reasons: [],
    evaluated_at: "2026-01-01T00:00:00+00:00",
    run_mode: "TEST",
    local_only: true,
    host_state: "READY",
    ...overrides,
  };
}

async function expectUnexpected(payload: Record<string, unknown>, status = 200) {
  server.use(http.get(READINESS_PATH, () => HttpResponse.json(payload, { status })));
  await expect(readReadiness(readinessClient())).rejects.toBeInstanceOf(UnexpectedResponse);
}

describe("readiness", () => {
  it("maps typed 200 + ready=true + READY to READY with the payload preserved", async () => {
    const payload = readinessPayload();
    server.use(http.get(READINESS_PATH, () => HttpResponse.json(payload)));

    await expect(readReadiness(readinessClient())).resolves.toEqual({ kind: "READY", payload });
  });

  it.each(["FAIL_CLOSED", "DEGRADED"] as const)(
    "maps typed 503 + ready=false + %s to NOT_READY without changing its error category",
    async (status) => {
      const payload = readinessPayload({
        ready: false,
        status,
        reasons: ["HOST_DISABLED"],
        host_state: status,
      });
      server.use(
        http.get(READINESS_PATH, () => HttpResponse.json(payload, { status: 503 })),
      );

      const result = await readReadiness(readinessClient());

      expect(result).toEqual({ kind: "NOT_READY", payload });
      expect(result).not.toBeInstanceOf(NetworkError);
      expect(result).not.toBeInstanceOf(HttpError);
      expect(result).not.toBeInstanceOf(Error);
    },
  );

  it("does not automatically retry a valid 503 readiness response", async () => {
    let requests = 0;
    const payload = readinessPayload({
      ready: false,
      status: "FAIL_CLOSED",
      reasons: ["HOST_DISABLED"],
      host_state: null,
    });
    server.use(
      http.get(READINESS_PATH, () => {
        requests += 1;
        return HttpResponse.json(payload, { status: 503 });
      }),
    );

    const result = await createQueryClient().fetchQuery({
      queryKey: ["readiness"],
      queryFn: () => readReadiness(readinessClient()),
    });

    expect(result.kind).toBe("NOT_READY");
    expect(requests).toBe(1);
  });

  it("rejects HTTP/body verdict mismatches", async () => {
    await expectUnexpected(
      readinessPayload({ ready: false, status: "FAIL_CLOSED", host_state: "FAIL_CLOSED" }),
    );
    await expectUnexpected(readinessPayload(), 503);
  });

  it("rejects malformed typed bodies", async () => {
    await expectUnexpected({});
    await expectUnexpected({ ...readinessPayload(), ready: undefined });
    await expectUnexpected({ ...readinessPayload(), ready: "true" });
    await expectUnexpected({ ...readinessPayload(), reasons: "HOST_DISABLED" });
    await expectUnexpected({ ...readinessPayload(), evaluated_at: undefined });
  });

  it("rejects internal ready/status contradictions", async () => {
    await expectUnexpected(readinessPayload({ status: "FAIL_CLOSED" }));
    await expectUnexpected(
      readinessPayload({ ready: false, status: "READY", host_state: "READY" }),
      503,
    );
  });

  it("rejects malformed non-JSON 503 as an unexpected response", async () => {
    server.use(
      http.get(READINESS_PATH, () =>
        HttpResponse.text("<html>gateway error</html>", {
          status: 503,
          headers: { "content-type": "text/html" },
        }),
      ),
    );

    await expect(readReadiness(readinessClient())).rejects.toBeInstanceOf(UnexpectedResponse);
  });

  it("keeps ordinary 500 as HttpError", async () => {
    server.use(
      http.get(READINESS_PATH, () => HttpResponse.json({ detail: "error" }, { status: 500 })),
    );

    await expect(readReadiness(readinessClient())).rejects.toBeInstanceOf(HttpError);
  });

  it("rejects other successful statuses instead of treating them as READY", async () => {
    server.use(
      http.get(READINESS_PATH, () => HttpResponse.json(readinessPayload(), { status: 201 })),
    );

    await expect(readReadiness(readinessClient())).rejects.toBeInstanceOf(UnexpectedResponse);
  });

  it("keeps protected 401 as UnauthorizedError", async () => {
    server.use(http.get(READINESS_PATH, () => HttpResponse.json({}, { status: 401 })));

    await expect(readReadiness(readinessClient())).rejects.toBeInstanceOf(UnauthorizedError);
  });
});
