import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { AppProviders } from "../app/AppProviders";
import { AppRoutes } from "../app/router";
import { AuthSessionProvider } from "../auth/AuthSessionProvider";
import { writeAccessToken } from "../auth/session";
import { TEST_ACCESS_TOKEN } from "./handlers";
import { ProtectedRequestProbe } from "./probe";

/** Establishes a session exactly the way a successful login does, before render. */
export function seedSession(token: string = TEST_ACCESS_TOKEN): void {
  writeAccessToken(token);
}

export interface RenderAppOptions {
  /** Entry history. Defaults to `/`, the redirect root. */
  readonly initialEntries?: readonly string[];
  /**
   * When present, mounts a probe that issues one authenticated protected request
   * inside the provider tree, so the `401` lifecycle can be observed end to end.
   */
  readonly protectedProbe?: {
    readonly onSettled?: () => void;
    readonly onRejected?: (error: unknown) => void;
  };
}

/**
 * Renders the real application tree with a controllable entry route.
 *
 * Same providers, same routes, same transport as `App.tsx` — only `MemoryRouter`
 * replaces `BrowserRouter` so a test can choose where it starts.
 */
export function renderApp(options: RenderAppOptions = {}) {
  const { initialEntries = ["/"], protectedProbe } = options;

  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[...initialEntries]}>
        <AuthSessionProvider>
          <AppRoutes />
          {protectedProbe === undefined ? null : (
            <ProtectedRequestProbe
              onSettled={protectedProbe.onSettled}
              onRejected={protectedProbe.onRejected}
            />
          )}
        </AuthSessionProvider>
      </MemoryRouter>
    </AppProviders>,
  );
}
