import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { queryClient } from "./queryClient";

/**
 * The single composition point for application-wide providers.
 *
 * Only the QueryClient lives here: UI V1 has no other global client store
 * (UI-F01 §12 — no Redux / Zustand / MobX / XState).
 */
export function AppProviders({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
