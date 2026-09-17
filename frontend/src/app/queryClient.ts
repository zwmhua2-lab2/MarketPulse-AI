import { QueryClient } from "@tanstack/react-query";

import { HttpError, NetworkError, UnauthorizedError } from "../api/errors";

/** Bounded retry budget for the whole application. */
export const MAX_QUERY_RETRIES = 2;

/**
 * Foundation retry policy (UI-F01 §11).
 *
 * - `401` is never retried: the session is gone, retrying cannot help.
 * - ordinary `4xx` is never retried: it is a deterministic client outcome.
 * - `/ready` `503` never reaches this predicate at all — it is interpreted as a
 *   successful `NOT_READY` transport result, not as an error (see `api/readiness.ts`).
 * - network failures and retryable `5xx` get a bounded retry only.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_QUERY_RETRIES) {
    return false;
  }
  if (error instanceof UnauthorizedError) {
    return false;
  }
  if (error instanceof HttpError) {
    return error.status >= 500;
  }
  return error instanceof NetworkError;
}

/**
 * Creates the application QueryClient.
 *
 * Owns server request lifecycle, response cache, request deduplication, refetch
 * coordination and invalidation — and nothing else. It deliberately does not own
 * MarketPulse business freshness: TanStack Query cache `stale` is never the UI's
 * `FRESH / STALE` (UI-V1-D01 §4.3, §8).
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetryQuery,
        // No global polling and no global refetch interval: freshness is the backend's
        // authority and every read surface chooses its own cadence when it is built.
        refetchInterval: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
      },
    },
  });
}

/**
 * The single application QueryClient instance.
 *
 * One per running application — never one per component and never per page.
 */
export const queryClient = createQueryClient();
