import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { TEST_PASSWORD, TEST_USERNAME } from "../test/handlers";
import { renderApp, seedSession } from "../test/render";
import { LOGIN_ROUTE, PRODUCT_ROUTES } from "./routes";

/** The five top-level product paths frozen by UI-V1-D01 §5. */
const FROZEN_PRODUCT_PATHS = ["/overview", "/market", "/research", "/trading", "/system"];

describe("route topology", () => {
  it("declares exactly the five frozen top-level product routes", () => {
    expect(PRODUCT_ROUTES.map((route) => route.path)).toEqual(FROZEN_PRODUCT_PATHS);
  });

  it("has no top-level AI route and keeps the Auth Shell out of the product IA", () => {
    const paths = PRODUCT_ROUTES.map((route) => route.path);
    expect(paths).not.toContain("/ai");
    expect(paths).not.toContain(LOGIN_ROUTE);
  });

  it("PAGE-02: redirects anonymous / to market", async () => {
    renderApp({ initialEntries: ["/"] });

    expect(await screen.findByRole("heading", { name: "市场与机会" })).toBeInTheDocument();
  });

  it.each(PRODUCT_ROUTES)("PAGE-01: anonymous $path opens its page", async ({ path, title, ownerBatch }) => {
    renderApp({ initialEntries: [path] });

    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "登录" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "退出登录" })).not.toBeInTheDocument();
    if (path !== "/market") {
      expect(screen.getByText(`${title} — 将在 ${ownerBatch} 实现`)).toBeInTheDocument();
    }
  });

  it.each(PRODUCT_ROUTES)("PAGE-03: session can open $path", async ({ path, title }) => {
    seedSession();
    renderApp({ initialEntries: [path] });
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "登录" })).not.toBeInTheDocument();
  });

  it("never renders an AI product page for /ai", async () => {
    seedSession();
    renderApp({ initialEntries: ["/ai"] });

    expect(await screen.findByRole("heading", { name: "总览" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /AI/ })).not.toBeInTheDocument();
  });

  it("renders every product route as a placeholder rather than business UI", async () => {
    seedSession();
    renderApp({ initialEntries: ["/system"] });

    expect(await screen.findByRole("heading", { name: "系统" })).toBeInTheDocument();
    expect(screen.getByText("系统 — 将在 UI-I01 实现")).toBeInTheDocument();
  });

  it("PAGE-04: direct login remains compatible", async () => {
    const user = userEvent.setup();
    renderApp({ initialEntries: ["/login"] });
    await screen.findByRole("heading", { name: "登录" });

    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(await screen.findByRole("heading", { name: "总览" })).toBeInTheDocument();
  });
});
