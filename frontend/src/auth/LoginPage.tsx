import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router";

import { DEFAULT_PRODUCT_ROUTE } from "../app/routes";
import { useAuthSession, type SignInFailure } from "./AuthSessionProvider";

const FAILURE_TEXT: Record<SignInFailure, string> = {
  "invalid-credentials": "用户名或密码不正确。",
  unavailable: "登录服务当前不可用，请稍后再试。",
};

/** Reads the retained target written by `RequireAuth`, rejecting anything not same-application. */
function readIntendedRoute(state: unknown): string | null {
  if (typeof state !== "object" || state === null) {
    return null;
  }
  const intended = (state as { intended?: unknown }).intended;
  if (typeof intended !== "string" || !intended.startsWith("/") || intended.startsWith("//")) {
    return null;
  }
  return intended;
}

/**
 * The Login boundary.
 *
 * The password lives in component-local React state for the duration of the submit
 * and is never written to any storage, cache, log or generated state (UI-F01 §7).
 *
 * A `401` from the login POST means invalid credentials: this page shows the failure
 * and stays put. It never clears the session or navigates, so it cannot create a
 * redirect loop (UI-F01 §8).
 */
export function LoginPage() {
  const { signIn } = useAuthSession();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [failure, setFailure] = useState<SignInFailure | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const intended = readIntendedRoute(location.state) ?? DEFAULT_PRODUCT_ROUTE;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }
    setSubmitting(true);
    setFailure(null);

    const result = await signIn({ username, password });

    setSubmitting(false);
    if (result.ok) {
      navigate(intended, { replace: true });
      return;
    }
    setPassword("");
    setFailure(result.reason);
  }

  return (
    <main className="login">
      <form className="login__form" onSubmit={onSubmit}>
        <p className="eyebrow">MARKETPULSE AI · V1</p>
        <h1>登录</h1>

        <label htmlFor="login-username">用户名</label>
        <input
          id="login-username"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />

        <label htmlFor="login-password">密码</label>
        <input
          id="login-password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "登录中…" : "登录"}
        </button>

        {failure === null ? null : (
          <p className="login__failure" role="alert">
            {FAILURE_TEXT[failure]}
          </p>
        )}
      </form>
    </main>
  );
}
