import { describe, expect, it } from "vitest";

import { HttpError, NetworkError, UnauthorizedError } from "../api/errors";
import { MAX_QUERY_RETRIES, createQueryClient, queryClient, shouldRetryQuery } from "./queryClient";

describe("query client", () => {
  it("operates as the server-state cache", async () => {
    const client = createQueryClient();
    const value = await client.fetchQuery({ queryKey: ["value"], queryFn: async () => 42 });

    expect(value).toBe(42);
    expect(client.getQueryData(["value"])).toBe(42);
  });

  it("leaves duplicate request behaviour to TanStack Query", async () => {
    const client = createQueryClient();
    let calls = 0;
    const queryFn = async () => {
      calls += 1;
      return "value";
    };

    const results = await Promise.all([
      client.fetchQuery({ queryKey: ["duplicate"], queryFn }),
      client.fetchQuery({ queryKey: ["duplicate"], queryFn }),
    ]);

    expect(results).toEqual(["value", "value"]);
    expect(calls).toBe(1);
  });

  it("does not retry a 401", async () => {
    const client = createQueryClient();
    let attempts = 0;

    await client
      .fetchQuery({
        queryKey: ["unauthorized"],
        queryFn: async () => {
          attempts += 1;
          throw new UnauthorizedError();
        },
      })
      .catch(() => undefined);

    expect(attempts).toBe(1);
  });

  it("applies the frozen retry policy", () => {
    expect(shouldRetryQuery(0, new UnauthorizedError())).toBe(false);
    expect(shouldRetryQuery(0, new HttpError(400, null))).toBe(false);
    expect(shouldRetryQuery(0, new HttpError(404, null))).toBe(false);
    expect(shouldRetryQuery(0, new HttpError(500, null))).toBe(true);
    expect(shouldRetryQuery(0, new HttpError(503, null))).toBe(true);
    expect(shouldRetryQuery(0, new NetworkError())).toBe(true);
    expect(shouldRetryQuery(0, new Error("unclassified"))).toBe(false);
    expect(shouldRetryQuery(MAX_QUERY_RETRIES, new NetworkError())).toBe(false);
    expect(shouldRetryQuery(MAX_QUERY_RETRIES + 5, new HttpError(500, null))).toBe(false);
  });

  it("has no default polling and no global refetch interval", () => {
    const defaults = queryClient.getDefaultOptions().queries;

    expect(defaults?.refetchInterval ?? false).toBe(false);
    expect(defaults?.refetchOnWindowFocus).toBe(false);
  });

  it("is a single application instance", () => {
    expect(queryClient).toBe(queryClient);
    expect(typeof queryClient.getQueryCache).toBe("function");
  });
});
