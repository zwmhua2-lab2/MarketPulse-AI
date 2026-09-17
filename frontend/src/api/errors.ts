/**
 * Transport-level error categories.
 *
 * These describe *how* a request failed, never what a response *means*. Product
 * capability semantics (readiness, risk admission, activation state, business
 * freshness) are owned by the backend payload and must never be re-encoded here.
 * See UI-V1-D01 §4.3 / §28.
 */

export type ApiErrorKind = "unauthorized" | "http" | "network" | "unexpected-response";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;

  constructor(kind: ApiErrorKind, message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = new.target.name;
    this.kind = kind;
  }
}

/**
 * The bearer session was rejected on a request that is not a credential check.
 *
 * This is the only category that is allowed to invalidate a session.
 */
export class UnauthorizedError extends ApiError {
  readonly status = 401;

  constructor(message = "认证已失效") {
    super("unauthorized", message);
  }
}

/** Any other non-2xx HTTP response, with the status and (when parsed) the body retained. */
export class HttpError extends ApiError {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown, message?: string) {
    super("http", message ?? `请求失败（HTTP ${status}）`);
    this.status = status;
    this.body = body;
  }
}

/** The request never produced an HTTP response (offline, DNS failure, connection reset). */
export class NetworkError extends ApiError {
  constructor(message = "网络请求失败", options?: { cause?: unknown }) {
    super("network", message, options);
  }
}

/** A response arrived but carried no interpretable JSON body. */
export class UnexpectedResponse extends ApiError {
  constructor(message = "响应格式无法解析", options?: { cause?: unknown }) {
    super("unexpected-response", message, options);
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}
