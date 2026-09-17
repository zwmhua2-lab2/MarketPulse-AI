import type { ApiClient } from "./client";
import { UnexpectedResponse } from "./errors";
import { sendRequest, transportErrorForStatus } from "./transport";

/** The frozen readiness endpoint (UI-V1-D01 §28). */
export const READINESS_PATH = "/api/v1/ready";

export type ReadinessKind = "READY" | "NOT_READY";

/**
 * The interpreted readiness outcome.
 *
 * `NOT_READY` is a *successfully interpreted* result, not a failure: the backend
 * answered authoritatively and its payload is preserved verbatim. Readiness is not
 * risk admission, so nothing here may be turned into a risk-admission judgement.
 */
export interface ReadinessResult {
  readonly kind: ReadinessKind;
  readonly payload: Record<string, unknown>;
}

function asReadinessPayload(value: unknown, context: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new UnexpectedResponse(`运行就绪响应缺少可解析的 JSON 对象（${context}）`);
  }
  return value as Record<string, unknown>;
}

/**
 * Reads `GET /api/v1/ready`.
 *
 * The backend contract is `200` = READY payload and `503` = authoritative NOT READY
 * payload. A `503` therefore never becomes a `NetworkError`, never becomes a generic
 * "backend unavailable" and never becomes an `HttpError` — and, because it resolves
 * successfully instead of throwing, it is never retried. The body is preserved so the
 * UI can render the real reason.
 *
 * This endpoint is the single explicit exception to the generic transport
 * interpretation (`api/transport.ts`): readiness is an authoritative *capability
 * payload* carried on a non-2xx status, which generic interpretation must not know
 * about. Hence the raw request step first, the `503` interception, and only then the
 * shared interpretation for everything else. No other module may take this shortcut.
 */
export async function readReadiness(client: ApiClient): Promise<ReadinessResult> {
  const outcome = await sendRequest(() => client.GET(READINESS_PATH));

  const { response } = outcome;
  const body: unknown = response.ok ? outcome.data : outcome.error;

  if (response.status === 503) {
    return { kind: "NOT_READY", payload: asReadinessPayload(body, "HTTP 503") };
  }

  const failure = transportErrorForStatus(response.status, body);
  if (failure !== null) {
    throw failure;
  }

  return { kind: "READY", payload: asReadinessPayload(body, `HTTP ${response.status}`) };
}
