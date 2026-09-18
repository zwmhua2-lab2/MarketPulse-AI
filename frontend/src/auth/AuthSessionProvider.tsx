import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { createApiClient, type ApiClient } from "../api/client";
import { clearAccessToken, readAccessToken, writeAccessToken } from "./session";

export type AuthStatus = "authenticated" | "unauthenticated";

/** Why a login attempt did not produce a session. */
export type SignInFailure = "invalid-credentials" | "unavailable";

export type SignInResult = { readonly ok: true } | { readonly ok: false; readonly reason: SignInFailure };

export interface Credentials {
  readonly username: string;
  readonly password: string;
}

export interface AuthSession {
  readonly status: AuthStatus;
  readonly accessToken: string | null;
  /** The API transport, bound to this session's bearer token. */
  readonly client: ApiClient;
  signIn(credentials: Credentials): Promise<SignInResult>;
  signOut(): void;
}

const AuthSessionContext = createContext<AuthSession | null>(null);

/**
 * The one Auth Session Boundary.
 *
 * It owns the bearer token, a local-only session generation, its Provider-lifetime
 * active state, the API transport bound to that token, and what happens when the backend
 * rejects the session. It does not parse the token, does not decide whether a token is
 * still valid, and does not invent a refresh mechanism — the backend's `401` is the only
 * auth authority (UI-F01 §7, §8).
 *
 * On an authoritative `401` it clears the persisted token and the authenticated Query
 * cache; navigation to the Login boundary is then a declarative consequence of the
 * session becoming unauthenticated (see `RequireAuth.tsx`).
 *
 * Passwords never reach this module: `signIn` takes them as arguments and hands them
 * straight to the login POST.
 */
export function AuthSessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [accessToken, setAccessToken] = useState<string | null>(() => readAccessToken());

  // The transport reads the token on every request, so an always-current ref keeps the
  // client instance stable across token changes instead of rebuilding it.
  const tokenRef = useRef<string | null>(accessToken);
  // Symbols are local-only identities. A new Provider lifetime and every session
  // transition receive a fresh identity without deriving anything from the bearer.
  const generationRef = useRef<symbol>(Symbol("marketpulse-session-generation"));
  // This is deliberately separate from session generation. A real unmount must
  // prevent the old client from mutating a shared QueryClient, while StrictMode's
  // development-only Effect cleanup/setup cycle must not stale-fence the current
  // session generation.
  const providerActiveRef = useRef(true);

  const advanceGeneration = useCallback(() => {
    generationRef.current = Symbol("marketpulse-session-generation");
  }, []);

  const endSession = useCallback(() => {
    // Advance first so every already-dispatched request becomes stale before token or
    // cache teardown. This also fences sibling late 401 responses.
    advanceGeneration();
    tokenRef.current = null;
    clearAccessToken();
    setAccessToken(null);
    queryClient.clear();
  }, [advanceGeneration, queryClient]);

  useLayoutEffect(
    () => {
      providerActiveRef.current = true;

      return () => {
        // Layout cleanup runs synchronously with the real unmount commit. An old
        // client therefore cannot clear a QueryClient adopted by a newly committed
        // Provider lifetime. Do not change session generation here.
        providerActiveRef.current = false;
      };
    },
    [],
  );

  const client = useMemo(
    () =>
      createApiClient({
        getToken: () => tokenRef.current,
        getSessionGeneration: () => generationRef.current,
        getProviderActive: () => providerActiveRef.current,
        onUnauthorized: endSession,
      }),
    [endSession],
  );

  const signIn = useCallback(
    async ({ username, password }: Credentials): Promise<SignInResult> => {
      let outcome;
      try {
        outcome = await client.POST("/api/v1/auth/login", { body: { username, password } });
      } catch {
        return { ok: false, reason: "unavailable" };
      }

      if (outcome.response.status === 401) {
        // Invalid credentials. This is not a session invalidation: stay unauthenticated
        // on the Login boundary without clearing or navigating.
        return { ok: false, reason: "invalid-credentials" };
      }

      const token = outcome.data?.access_token;
      if (!outcome.response.ok || token === undefined || token === "") {
        return { ok: false, reason: "unavailable" };
      }

      // A successful login begins a new local request-ownership lifetime before the
      // token becomes visible to subsequent protected dispatches.
      advanceGeneration();
      tokenRef.current = token;
      writeAccessToken(token);
      setAccessToken(token);
      return { ok: true };
    },
    [advanceGeneration, client],
  );

  const signOut = useCallback(() => {
    endSession();
  }, [endSession]);

  const value = useMemo<AuthSession>(
    () => ({
      status: accessToken === null ? "unauthenticated" : "authenticated",
      accessToken,
      client,
      signIn,
      signOut,
    }),
    [accessToken, client, signIn, signOut],
  );

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession(): AuthSession {
  const value = useContext(AuthSessionContext);
  if (value === null) {
    throw new Error("useAuthSession 必须在 <AuthSessionProvider> 内使用");
  }
  return value;
}

/** The API transport bound to the current session. */
export function useApiClient(): ApiClient {
  return useAuthSession().client;
}
