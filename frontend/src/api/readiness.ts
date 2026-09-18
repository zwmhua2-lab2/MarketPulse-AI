import type { ApiClient } from "./client";
import { UnexpectedResponse } from "./errors";
import type { components } from "./generated";
import { sendRequest, transportErrorForStatus } from "./transport";

/** The frozen readiness endpoint (UI-V1-D01 §28). */
export const READINESS_PATH = "/api/v1/ready";

export type ReadinessKind = "READY" | "NOT_READY";
export type ReadinessPayload = components["schemas"]["ReadinessResponse"];

const readinessStatuses = new Set<ReadinessPayload["status"]>([
  "READY",
  "NOT_READY",
  "DEGRADED",
  "FAIL_CLOSED",
]);

/**
 * The interpreted readiness outcome.
 *
 * `NOT_READY` is a *successfully interpreted* result, not a failure: the backend
 * answered authoritatively and its payload is preserved verbatim. Readiness is not
 * risk admission, so nothing here may be turned into a risk-admission judgement.
 */
export interface ReadinessResult {
  readonly kind: ReadinessKind;
  readonly payload: ReadinessPayload;
}

function asReadinessPayload(value: unknown, context: string): ReadinessPayload {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new UnexpectedResponse(`运行就绪响应缺少可解析的 JSON 对象（${context}）`);
  }
  const payload = value as Record<string, unknown>;
  if (
    typeof payload.ready !== "boolean" ||
    typeof payload.status !== "string" ||
    !readinessStatuses.has(payload.status as ReadinessPayload["status"]) ||
    !Array.isArray(payload.reasons) ||
    !payload.reasons.every((reason) => typeof reason === "string") ||
    typeof payload.evaluated_at !== "string" ||
    typeof payload.run_mode !== "string" ||
    typeof payload.local_only !== "boolean" ||
    (payload.host_state !== null && typeof payload.host_state !== "string")
  ) {
    throw new UnexpectedResponse(`运行就绪响应不符合 typed contract（${context}）`);
  }
  if (payload.ready !== (payload.status === "READY")) {
    throw new UnexpectedResponse(`运行就绪响应 ready/status 不一致（${context}）`);
  }
  return payload as ReadinessPayload;
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
  const body: unknown = response.status === 200 ? outcome.data : outcome.error;

  if (response.status === 200) {
    const payload = asReadinessPayload(body, "HTTP 200");
    if (!payload.ready) {
      throw new UnexpectedResponse("HTTP 200 readiness payload is not READY");
    }
    return { kind: "READY", payload };
  }

  if (response.status === 503) {
    const payload = asReadinessPayload(body, "HTTP 503");
    if (payload.ready) {
      throw new UnexpectedResponse("HTTP 503 readiness payload is READY");
    }
    return { kind: "NOT_READY", payload };
  }

  const failure = transportErrorForStatus(response.status, body);
  if (failure !== null) {
    throw failure;
  }

  throw new UnexpectedResponse(`不支持的 readiness 成功状态（HTTP ${response.status}）`);
}
