import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { createQueryClient } from "../app/queryClient";
import { server } from "../test/server";
import { createApiClient } from "./client";
import { HttpError, NetworkError, UnauthorizedError } from "./errors";
import { READINESS_PATH, readReadiness } from "./readiness";

function readinessClient() {
  return createApiClient({ getToken: () => null, onUnauthorized: () => undefined });
}

describe("readiness", () => {
  it("maps 200 to the READY semantic result with the payload preserved", async () => {
    const payload = { ready: true, run_mode: "TEST", local_only: true, reasons: [] };
    server.use(http.get(READINESS_PATH, () => HttpResponse.json(payload)));

    const result = await readReadiness(readinessClient());

    expect(result.kind).toBe("READY");
    expect(result.payload).toEqual(payload);
  });

  it("maps 503 with a valid body to the NOT_READY semantic result and preserves the body", async () => {
    const payload = {
      ready: false,
      run_mode: "TEST",
      local_only: true,
      reasons: ["HOST_DISABLED"],
    };
    server.use(http.get(READINESS_PATH, () => HttpResponse.json(payload, { status: 503 })));

    const result = await readReadiness(readinessClient());

    expect(result.kind).toBe("NOT_READY");
    expect(result.payload).toEqual(payload);
  });

  it("does not classify a 503 readiness response as a transport failure", async () => {
    server.use(
      http.get(READINESS_PATH, () =>
        HttpResponse.json({ ready: false, reasons: ["NOT_READY"] }, { status: 503 }),
      ),
    );

    // Resolving at all is the point: a NetworkError, a generic backend outage or any
    // other transport failure would have been thrown instead of returned.
    await expect(readReadiness(readinessClient())).resolves.toMatchObject({ kind: "NOT_READY" });

    const result = await readReadiness(readinessClient());
    expect(result).not.toBeInstanceOf(NetworkError);
    expect(result).not.toBeInstanceOf(HttpError);
    expect(result).not.toBeInstanceOf(Error);
  });

  it("is not automatically retried on 503", async () => {
    let requests = 0;
    server.use(
      http.get(READINESS_PATH, () => {
        requests += 1;
        return HttpResponse.json({ ready: false, reasons: ["NOT_READY"] }, { status: 503 });
      }),
    );

    const client = readinessClient();
    const result = await createQueryClient().fetchQuery({
      queryKey: ["readiness"],
      queryFn: () => readReadiness(client),
    });

    expect(result.kind).toBe("NOT_READY");
    expect(requests).toBe(1);
  });

  it("raises a distinct error when a 503 body is not an interpretable readiness payload", async () => {
    server.use(
      http.get(READINESS_PATH, () =>
        HttpResponse.text("<html>gateway error</html>", {
          status: 503,
          headers: { "content-type": "text/html" },
        }),
      ),
    );

    const failure = await readReadiness(readinessClient()).catch((cause: unknown) => cause);

    expect(failure).toBeInstanceOf(Error);
    expect(failure).not.toBeInstanceOf(NetworkError);
    expect(failure).not.toBeInstanceOf(HttpError);
    expect(failure).not.toBeInstanceOf(UnauthorizedError);
  });
});
