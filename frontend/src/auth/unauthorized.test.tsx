import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { queryClient } from "../app/queryClient";
import { AUTH_TOKEN_STORAGE_KEY, readAccessToken } from "./session";
import { LOGIN_PATH, PROTECTED_PING_PATH, TEST_PASSWORD, TEST_USERNAME } from "../test/handlers";
import { renderApp, seedSession } from "../test/render";
import { server } from "../test/server";

/** The backend rejects this session regardless of the token the client presents. */
function rejectSession(): void {
  server.use(
    http.get(PROTECTED_PING_PATH, () =>
      HttpResponse.json({ detail: "invalid session" }, { status: 401 }),
    ),
  );
}

describe("protected API 401", () => {
  it("clears the session, clears the authenticated query cache and enters the Login boundary", async () => {
    rejectSession();
    seedSession();
    queryClient.setQueryData(["authenticated-probe"], { cached: "authenticated data" });

    renderApp({
      initialEntries: ["/trading"],
      protectedProbe: {},
    });

    expect(await screen.findByRole("heading", { name: "登录" })).toBeInTheDocument();

    await waitFor(() => {
      expect(readAccessToken()).toBeNull();
    });
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(queryClient.getQueryData(["authenticated-probe"])).toBeUndefined();
  });

  it("retains the safe intended route and returns to it after re-authentication", async () => {
    rejectSession();
    seedSession();
    renderApp({ initialEntries: ["/research"], protectedProbe: {} });

    await screen.findByRole("heading", { name: "登录" });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(await screen.findByRole("heading", { name: "策略研究" })).toBeInTheDocument();
  });
});

describe("login 401", () => {
  it("stays a login error without navigating and without a redirect loop", async () => {
    let loginRequests = 0;
    server.use(
      http.post(LOGIN_PATH, () => {
        loginRequests += 1;
        return HttpResponse.json({ detail: "invalid credentials" }, { status: 401 });
      }),
    );

    const user = userEvent.setup();
    renderApp({ initialEntries: ["/login"] });

    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), "definitely-not-the-password");
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("用户名或密码不正确。");
    expect(readAccessToken()).toBeNull();

    // Give any erroneous clear/navigate loop a chance to surface.
    await new Promise((resolve) => {
      setTimeout(resolve, 50);
    });

    expect(loginRequests).toBe(1);
    expect(screen.getByRole("heading", { name: "登录" })).toBeInTheDocument();
  });
});
