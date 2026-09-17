/**
 * The Foundation-owned generic transport interpretation.
 *
 * `openapi-fetch` never throws on a non-2xx response: it resolves with
 * `{ data, error, response }` and leaves the HTTP verdict to the caller. Without one
 * shared interpretation step, every Product Query module would have to reproduce the
 * same four checks itself — catch the network exception, inspect `response.ok`, map
 * `401`, and map ordinary `4xx` / `5xx`.
 *
 * This module is that one step (UI-F01 §4, closing UI-F01-I01-R1):
 *
 *   openapi-fetch
 *     ↓ generic MarketPulse transport interpretation
 *       ├─ network failure            → NetworkError
 *       ├─ 401                        → UnauthorizedError
 *       ├─ any other non-2xx          → HttpError (status + body preserved)
 *       └─ 2xx with an interpretable body → typed data
 *     ↓ domain query
 *
 * Product capability semantics are never inferred here. In particular this module has
 * no notion of readiness, risk admission, activation state or business freshness: a
 * `503` is an ordinary `HttpError` to every caller except the one endpoint that defines
 * it as an authoritative payload (`api/readiness.ts`, the single explicit exception).
 */

import { HttpError, NetworkError, UnauthorizedError, UnexpectedResponse } from "./errors";

/**
 * An `openapi-fetch` outcome, reduced to what transport interpretation needs.
 *
 * Structurally compatible with `FetchResponse` for the generated `paths`, so an
 * operation can be passed as `() => client.GET(path)` and its success body type is
 * inferred into `T`.
 */
export interface TransportOutcome<T> {
  /** The parsed success body, present only on a 2xx response. */
  readonly data?: T;
  /** The parsed error body, present only on a non-2xx response. */
  readonly error?: unknown;
  /** The raw response. Always present: it carries the status. */
  readonly response: Response;
}

/** A single endpoint operation, as handed to the interpretation step. */
export type TransportCall<T> = () => Promise<TransportOutcome<T>>;

/**
 * Maps an HTTP status to a transport error category, or `null` when the response is
 * not a transport failure. Product capability semantics are never inferred here.
 */
export function transportErrorForStatus(status: number, body: unknown): Error | null {
  if (status === 401) {
    return new UnauthorizedError();
  }
  if (status < 200 || status >= 300) {
    return new HttpError(status, body);
  }
  return null;
}

/**
 * Waits for one request and normalizes a failure to produce a usable response.
 *
 * This is the network-level half of the interpretation, exposed separately because the
 * one endpoint with an authoritative non-2xx payload (`/ready`) has to inspect the raw
 * outcome before generic interpretation runs. It is not a second transport: it performs
 * no HTTP classification, and `/ready` remains its only consumer.
 *
 * `openapi-fetch` surfaces a response whose declared JSON body could not be parsed as
 * the parse error itself, which is not a network failure — reporting it as one would
 * mislabel a malformed response as an outage and let it be retried.
 */
export async function sendRequest<T>(call: TransportCall<T>): Promise<TransportOutcome<T>> {
  try {
    return await call();
  } catch (cause) {
    if (cause instanceof SyntaxError) {
      throw new UnexpectedResponse("响应体不是可解析的 JSON，无法解释本次响应", { cause });
    }
    throw new NetworkError("网络请求未完成", { cause });
  }
}

/**
 * Sends one request and interprets its outcome.
 *
 * On success the typed body is returned; otherwise a transport error is thrown. A 2xx
 * response that carries no interpretable JSON body is reported as `UnexpectedResponse`
 * rather than silently yielding `undefined` — every endpoint on the current contract
 * declares a JSON body. An endpoint that is genuinely bodyless would have to use the
 * raw step above instead of the generic interpreter.
 */
export async function requestData<T>(call: TransportCall<T>): Promise<T> {
  const outcome = await sendRequest(call);
  const { response } = outcome;

  const failure = transportErrorForStatus(response.status, outcome.error);
  if (failure !== null) {
    throw failure;
  }

  if (outcome.data === undefined) {
    throw new UnexpectedResponse(`响应缺少可解析的 JSON 响应体（HTTP ${response.status}）`);
  }

  return outcome.data;
}
