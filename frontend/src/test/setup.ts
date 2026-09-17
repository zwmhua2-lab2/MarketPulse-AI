import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { queryClient } from "../app/queryClient";
import { server } from "./server";

beforeAll(() => {
  // Unhandled requests are a test defect, not a silent pass: nothing in the frontend
  // foundation may reach for an endpoint the frozen contract does not declare.
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  // Registered explicitly: Testing Library's automatic cleanup hooks onto a global
  // `afterEach`, which does not exist while Vitest runs with `globals: false`.
  cleanup();
  server.resetHandlers();
  queryClient.clear();
  window.sessionStorage.clear();
  window.localStorage.clear();
});

afterAll(() => {
  server.close();
});
