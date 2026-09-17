import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Frontend test harness (UI-F01 §17).
 *
 * Tests run against a real jsdom document and intercept at the network boundary with
 * MSW, so the API client, the bearer attachment and the `401` lifecycle are exercised
 * as they are in the browser instead of being mocked away.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: false,
    restoreMocks: true,
    testTimeout: 15000,
  },
});
