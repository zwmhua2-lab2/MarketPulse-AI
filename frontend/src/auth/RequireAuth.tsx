import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { useAuthSession } from "./AuthSessionProvider";
import { LOGIN_ROUTE } from "../app/routes";

/** Router state carrying the route the operator actually wanted. */
export interface IntendedRouteState {
  readonly intended: string;
}

/**
 * The safe internal route to return to after login, or `null` when there is none.
 *
 * `/login` is excluded so a `401` can never bounce back into itself, and a
 * protocol-relative `//host` is rejected so the retained target can only ever be a
 * same-application path (UI-V1-D01 §25).
 */
export function intendedRouteOf(pathname: string, search: string): string | null {
  if (pathname === "" || pathname === LOGIN_ROUTE || pathname.startsWith("//")) {
    return null;
  }
  return pathname.startsWith("/") ? `${pathname}${search}` : null;
}

/**
 * Authentication gate for the product shell.
 *
 * When the session is gone — because it was never established, because the operator
 * signed out, or because the backend returned `401` and the transport boundary
 * cleared it — the operator lands on the Login boundary with the intended route
 * retained where practical.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuthSession();
  const location = useLocation();

  if (status !== "authenticated") {
    const intended = intendedRouteOf(location.pathname, location.search);
    return (
      <Navigate
        to={LOGIN_ROUTE}
        replace
        state={intended === null ? null : ({ intended } satisfies IntendedRouteState)}
      />
    );
  }

  return <>{children}</>;
}
