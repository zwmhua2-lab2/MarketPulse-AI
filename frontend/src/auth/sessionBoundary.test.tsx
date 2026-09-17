import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { AUTH_TOKEN_STORAGE_KEY, readAccessToken } from "./session";
import { PROTECTED_PING_PATH, TEST_ACCESS_TOKEN, TEST_PASSWORD, TEST_USERNAME } from "../test/handlers";
import { renderApp, seedSession } from "../test/render";
import { server } from "../test/server";

function storedValues(): string[] {
  const values: string[] = [];
  for (const storage of [window.sessionStorage, window.localStorage]) {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      values.push(key ?? "", storage.getItem(key ?? "") ?? "");
    }
  }
  return values;
}

async function loginThroughUi(): Promise<void> {
  const user = userEvent.setup();
  renderApp({ initialEntries: ["/login"] });
  await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
  await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);
  await user.click(screen.getByRole("button", { name: "登录" }));
  await screen.findByRole("heading", { name: "总览" });
}

describe("auth session boundary", () => {
  it("persists the bearer token only in the approved session boundary", async () => {
    await loginThroughUi();

    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe(TEST_ACCESS_TOKEN);
    expect(window.sessionStorage.length).toBe(1);
    expect(window.localStorage.length).toBe(0);
    expect(document.cookie).not.toContain(TEST_ACCESS_TOKEN);
  });

  it("never persists the password, at submission time or afterwards", async () => {
    const user = userEvent.setup();
    renderApp({ initialEntries: ["/login"] });

    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);

    // Typed but not yet submitted: still nothing anywhere.
    expect(storedValues().join("\u0000")).not.toContain(TEST_PASSWORD);

    await user.click(screen.getByRole("button", { name: "登录" }));
    await screen.findByRole("heading", { name: "总览" });

    expect(storedValues().join("\u0000")).not.toContain(TEST_PASSWORD);
    expect(document.cookie).not.toContain(TEST_PASSWORD);
  });

  it("injects the stored bearer token on protected requests", async () => {
    const seen: Array<string | null> = [];
    server.use(
      http.get(PROTECTED_PING_PATH, ({ request }) => {
        seen.push(request.headers.get("Authorization"));
        return HttpResponse.json({ status: "authenticated" });
      }),
    );

    seedSession();
    renderApp({ initialEntries: ["/overview"], protectedProbe: {} });

    await waitFor(() => {
      expect(seen).toHaveLength(1);
    });
    expect(seen[0]).toBe(`Bearer ${TEST_ACCESS_TOKEN}`);
  });

  it("clears the session on sign out", async () => {
    await loginThroughUi();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "退出登录" }));

    expect(readAccessToken()).toBeNull();
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(await screen.findByRole("heading", { name: "登录" })).toBeInTheDocument();
  });
});
