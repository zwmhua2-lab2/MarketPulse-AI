import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { Link, MemoryRouter } from "react-router";
import { AppProviders } from "../app/AppProviders";
import { AppRoutes } from "../app/router";
import { AuthSessionProvider } from "./AuthSessionProvider";
import { ProtectedRequestProbe } from "../test/probe";

import { queryClient } from "../app/queryClient";
import { AUTH_TOKEN_STORAGE_KEY, readAccessToken } from "./session";
import {
  LOGIN_PATH,
  PROTECTED_PING_PATH,
  TEST_ACCESS_TOKEN,
  TEST_PASSWORD,
  TEST_USERNAME,
} from "../test/handlers";
import { renderApp, seedSession } from "../test/render";
import { server } from "../test/server";
import { UnauthorizedError } from "../api/errors";

/** The backend rejects this session regardless of the token the client presents. */
function rejectSession(): void {
  server.use(
    http.get(PROTECTED_PING_PATH, () =>
      HttpResponse.json({ detail: "invalid session" }, { status: 401 }),
    ),
  );
}

function renderWithLoginNavigation(path: string, probe: { onRejected?: (error: unknown) => void; onSettled?: () => void } = {}) {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[path]}>
        <AuthSessionProvider>
          <AppRoutes />
          <Link to="/login" state={{ intended: path }}>显式登录</Link>
          <ProtectedRequestProbe {...probe} />
        </AuthSessionProvider>
      </MemoryRouter>
    </AppProviders>,
  );
}

describe("protected API 401", () => {
  it("remains authoritative after the production StrictMode Effect lifecycle", async () => {
    let markRequestDispatched: () => void = () => undefined;
    const requestDispatched = new Promise<void>((resolve) => {
      markRequestDispatched = resolve;
    });
    let releaseResponse: () => void = () => undefined;
    const responseReleased = new Promise<void>((resolve) => {
      releaseResponse = resolve;
    });
    let markRequestSettled: () => void = () => undefined;
    const requestSettled = new Promise<void>((resolve) => {
      markRequestSettled = resolve;
    });
    let requestFailure: unknown;

    server.use(
      http.get(PROTECTED_PING_PATH, async ({ request }) => {
        expect(request.headers.get("Authorization")).toBe(`Bearer ${TEST_ACCESS_TOKEN}`);
        markRequestDispatched();
        await responseReleased;
        return HttpResponse.json({ detail: "invalid current session" }, { status: 401 });
      }),
    );

    seedSession();
    queryClient.setQueryData(["authenticated-probe"], { cached: "authenticated data" });
    renderApp({
      initialEntries: ["/trading"],
      strictMode: true,
      protectedProbe: {
        onRejected: (error) => {
          requestFailure = error;
        },
        onSettled: markRequestSettled,
      },
    });
    await requestDispatched;

    // The StrictMode Effect stress cycle has completed without a sign-out, login,
    // or Provider replacement. This held request remains current-session authority.
    releaseResponse();
    await requestSettled;

    expect(requestFailure).toBeInstanceOf(UnauthorizedError);
    expect(readAccessToken()).toBeNull();
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(queryClient.getQueryData(["authenticated-probe"])).toBeUndefined();
    expect(await screen.findByRole("heading", { name: "交易与仓位" })).toBeInTheDocument();
  });

  it("clears the session and authenticated query cache while keeping the page accessible", async () => {
    rejectSession();
    seedSession();
    queryClient.setQueryData(["authenticated-probe"], { cached: "authenticated data" });

    renderApp({
      initialEntries: ["/trading"],
      protectedProbe: {},
    });

    expect(await screen.findByRole("heading", { name: "交易与仓位" })).toBeInTheDocument();

    await waitFor(() => {
      expect(readAccessToken()).toBeNull();
    });
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(queryClient.getQueryData(["authenticated-probe"])).toBeUndefined();
  });

  it("retains the safe intended route and returns to it after re-authentication", async () => {
    rejectSession();
    seedSession();
    renderWithLoginNavigation("/research");
    await waitFor(() => expect(readAccessToken()).toBeNull());
    expect(screen.getByRole("heading", { name: "策略研究" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("link", { name: "显式登录" }));
    await screen.findByRole("heading", { name: "登录" });
    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(await screen.findByRole("heading", { name: "策略研究" })).toBeInTheDocument();
  });

  it("keeps G2 authenticated when a pending G1 protected request returns 401 late", async () => {
    const oldToken = "OLD_TOKEN";
    const newToken = "NEW_TOKEN";
    let markOldRequestDispatched: () => void = () => undefined;
    const oldRequestDispatched = new Promise<void>((resolve) => {
      markOldRequestDispatched = resolve;
    });
    let releaseOldResponse: () => void = () => undefined;
    const oldResponseReleased = new Promise<void>((resolve) => {
      releaseOldResponse = resolve;
    });
    let markOldRequestSettled: () => void = () => undefined;
    const oldRequestSettled = new Promise<void>((resolve) => {
      markOldRequestSettled = resolve;
    });
    let oldRequestFailure: unknown;

    server.use(
      http.get(PROTECTED_PING_PATH, async ({ request }) => {
        expect(request.headers.get("Authorization")).toBe(`Bearer ${oldToken}`);
        markOldRequestDispatched();
        await oldResponseReleased;
        return HttpResponse.json({ detail: "invalid old session" }, { status: 401 });
      }),
      http.post(LOGIN_PATH, () =>
        HttpResponse.json({ access_token: newToken, token_type: "bearer" }),
      ),
    );

    seedSession(oldToken);
    renderWithLoginNavigation("/trading", {
      onRejected: (error) => { oldRequestFailure = error; },
      onSettled: markOldRequestSettled,
    });
    await oldRequestDispatched;

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "退出登录" }));
    expect(screen.getByRole("heading", { name: "交易与仓位" })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "显式登录" }));
    await screen.findByRole("heading", { name: "登录" });

    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);
    await user.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByRole("heading", { name: "交易与仓位" })).toBeInTheDocument();

    const g2Cache = { cached: "G2 authenticated data" };
    queryClient.setQueryData(["authenticated-probe"], g2Cache);

    releaseOldResponse();
    await oldRequestSettled;

    expect(oldRequestFailure).toBeInstanceOf(UnauthorizedError);
    expect(readAccessToken()).toBe(newToken);
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe(newToken);
    expect(screen.getByRole("heading", { name: "交易与仓位" })).toBeInTheDocument();
    expect(queryClient.getQueryData(["authenticated-probe"])).toEqual(g2Cache);
  });

  it("advances ownership on successful sign-in before an old protected 401 can act", async () => {
    const oldToken = "OLD_TOKEN";
    const newToken = "NEW_TOKEN";
    let markOldRequestDispatched: () => void = () => undefined;
    const oldRequestDispatched = new Promise<void>((resolve) => {
      markOldRequestDispatched = resolve;
    });
    let releaseOldResponse: () => void = () => undefined;
    const oldResponseReleased = new Promise<void>((resolve) => {
      releaseOldResponse = resolve;
    });
    let markOldRequestSettled: () => void = () => undefined;
    const oldRequestSettled = new Promise<void>((resolve) => {
      markOldRequestSettled = resolve;
    });
    let oldRequestFailure: unknown;

    server.use(
      http.get(PROTECTED_PING_PATH, async () => {
        markOldRequestDispatched();
        await oldResponseReleased;
        return HttpResponse.json({ detail: "invalid old session" }, { status: 401 });
      }),
      http.post(LOGIN_PATH, () =>
        HttpResponse.json({ access_token: newToken, token_type: "bearer" }),
      ),
    );

    seedSession(oldToken);
    renderApp({
      initialEntries: ["/login"],
      protectedProbe: {
        onRejected: (error) => {
          oldRequestFailure = error;
        },
        onSettled: markOldRequestSettled,
      },
    });
    await oldRequestDispatched;

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);
    await user.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByRole("heading", { name: "总览" })).toBeInTheDocument();

    const g2Cache = { cached: "replacement session data" };
    queryClient.setQueryData(["authenticated-probe"], g2Cache);
    releaseOldResponse();
    await oldRequestSettled;

    expect(oldRequestFailure).toBeInstanceOf(UnauthorizedError);
    expect(readAccessToken()).toBe(newToken);
    expect(screen.getByRole("heading", { name: "总览" })).toBeInTheDocument();
    expect(queryClient.getQueryData(["authenticated-probe"])).toEqual(g2Cache);
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
