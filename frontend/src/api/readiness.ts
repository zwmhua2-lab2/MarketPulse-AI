import type { ApiClient } from "./client";
import { HttpError, NetworkError, UnauthorizedError, UnexpectedResponse } from "./errors";

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
 * "backend unavailable", and — because it resolves successfully instead of throwing —
 * is never retried. The body is preserved so the UI can render the real reason.
 */
export async function readReadiness(client: ApiClient): Promise<ReadinessResult> {
  let outcome;
  try {
    outcome = await client.GET(READINESS_PATH);
  } catch (cause) {
    throw new NetworkError("读取运行就绪状态失败：网络请求未完成", { cause });
  }

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
