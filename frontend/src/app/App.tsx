import { BrowserRouter } from "react-router";

import { AuthSessionProvider } from "../auth/AuthSessionProvider";
import { AppProviders } from "./AppProviders";
import { AppRoutes } from "./router";

/**
 * Application root.
 *
 * Provider order is a contract, not a preference: the auth session boundary clears
 * the Query cache when the backend rejects the session, so it must sit inside the
 * QueryClientProvider. Tests render `AppProviders` + `MemoryRouter` + `AppRoutes`
 * directly (see `src/test/render.tsx`) so they can choose the entry route.
 */
export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AuthSessionProvider>
          <AppRoutes />
        </AuthSessionProvider>
      </BrowserRouter>
    </AppProviders>
  );
}
