/**
 * The one approved place a bearer access token may be persisted.
 *
 * `sessionStorage` is the frozen persistence choice for UI V1 (UI-V1-D01 §25).
 * Passwords are never written here — or anywhere else — by construction: this
 * module exposes no API that accepts one. See `LoginPage.tsx`, where the password
 * lives only in component-local React state for the duration of the submit.
 */

export const AUTH_TOKEN_STORAGE_KEY = "marketpulse.auth.access-token";

/** Reads the persisted access token, or `null` when there is no session. */
export function readAccessToken(storage: Storage = window.sessionStorage): string | null {
  const stored = storage.getItem(AUTH_TOKEN_STORAGE_KEY);
  return stored === null || stored === "" ? null : stored;
}

/** Persists the access token established by a successful `POST /api/v1/auth/login`. */
export function writeAccessToken(token: string, storage: Storage = window.sessionStorage): void {
  storage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

/** Drops the access token. Called on sign-out and on an authoritative `401`. */
export function clearAccessToken(storage: Storage = window.sessionStorage): void {
  storage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}
