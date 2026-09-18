import { useEffect, useRef } from "react";

import { useApiClient } from "../auth/AuthSessionProvider";
import { requestData } from "../api/transport";
import { PROTECTED_PING_PATH } from "./handlers";

export interface ProtectedRequestProbeProps {
  /** Called once the probe request has settled, successfully or not. */
  readonly onSettled?: () => void;
  /** Receives the real transport failure from the originating protected request. */
  readonly onRejected?: (error: unknown) => void;
}

/**
 * Test-only probe.
 *
 * Issues exactly one authenticated `GET /api/v1/protected/ping` through the
 * session-bound transport, so the bearer attachment and the `401` lifecycle are
 * exercised through the real API client instead of being mocked away.
 */
export function ProtectedRequestProbe({ onSettled, onRejected }: ProtectedRequestProbeProps) {
  const client = useApiClient();
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) {
      return;
    }
    fired.current = true;
    void requestData(() => client.GET(PROTECTED_PING_PATH))
      .catch((error: unknown) => onRejected?.(error))
      .finally(() => onSettled?.());
  }, [client, onRejected, onSettled]);

  return null;
}
