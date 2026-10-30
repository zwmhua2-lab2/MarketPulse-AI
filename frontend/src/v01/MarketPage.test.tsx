import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../test/server";
import { TEST_PASSWORD, TEST_USERNAME } from "../test/handlers";
import { renderApp, seedSession } from "../test/render";
import { PRODUCT_ROUTES } from "../app/routes";

const path = "/api/v1/product/market-candles";
const periodMs = { "5m": 300_000, "15m": 900_000, "1h": 3_600_000 } as const;
type Bar = keyof typeof periodMs;
const firstOpen = Date.UTC(2026, 9, 1);
const candle = (i: number, bar: Bar = "5m") => ({ open_time_ms: firstOpen + i * periodMs[bar], close_time_ms: firstOpen + (i + 1) * periodMs[bar], open: "1.00", high: "3.00", low: "0.50", close: i === 0 ? "2.00" : i === 59 ? "1.50" : "0.75", volume: "9.000", confirmed: true as const });
const payload = (instrument_id = "BTC-USDT", bar: Bar = "5m") => ({ instrument_id, bar, source: "OKX_PUBLIC_REST", data_quality: "FRESH", observed_at: "2026-10-30T00:00:00Z", items: Array.from({ length: 60 }, (_, i) => candle(i, bar)) });

describe("GWT-UI01-01～06 Market page", () => {
  it("GWT-UI01-01: unauthenticated /market is handled by Login before any candle GET; keeps five routes", async () => {
    let calls = 0;
    server.use(http.get(path, () => { calls++; return HttpResponse.json(payload()); }));
    renderApp({ initialEntries: ["/market"] });
    expect(await screen.findByRole("heading", { name: "登录" })).toBeInTheDocument();
    expect(calls).toBe(0);
    expect(PRODUCT_ROUTES.map((r) => r.path)).toEqual(["/overview", "/market", "/research", "/trading", "/system"]);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("用户名"), TEST_USERNAME);
    await user.type(screen.getByLabelText("密码"), TEST_PASSWORD);
    await user.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByRole("heading", { name: "市场与机会" })).toBeInTheDocument();
    await waitFor(() => expect(calls).toBe(1));
  });

  it("GWT-UI01-02: requests the selected instrument and bar through the authenticated same-origin API", async () => {
    seedSession();
    const requests: string[] = [];
    server.use(http.get(path, ({ request }) => {
      const url = new URL(request.url);
      expect(request.headers.get("authorization")).toMatch(/^Bearer /);
      requests.push(`${url.searchParams.get("instrument_id")}/${url.searchParams.get("bar")}`);
      return HttpResponse.json(payload(url.searchParams.get("instrument_id")!, url.searchParams.get("bar")! as Bar));
    }));
    const user = userEvent.setup(); renderApp({ initialEntries: ["/market"] });
    await screen.findByText("数据源：OKX_PUBLIC_REST");
    const coin = screen.getByLabelText("币种");
    const bar = screen.getByLabelText("周期");
    for (const instrument of ["ETH-USDT", "BTC-USDT"]) {
      await user.selectOptions(coin, instrument);
      for (const interval of ["5m", "15m", "1h"] as const) {
        await user.selectOptions(bar, interval);
        await waitFor(() => expect(requests.at(-1)).toBe(`${instrument}/${interval}`));
        await waitFor(() => {
          expect(screen.getAllByTestId("candle")).toHaveLength(60);
          expect(screen.getByText(`收盘时间：${new Date(firstOpen + 60 * periodMs[interval]).toISOString()}`)).toBeInTheDocument();
        });
      }
    }
    expect(requests).toContain("ETH-USDT/5m");
    expect(requests).toContain("BTC-USDT/1h");
  });

  it("GWT-UI01-03: draws 60 candles and shows source, observed time and original closed-candle values", async () => {
    seedSession(); server.use(http.get(path, () => HttpResponse.json(payload())));
    renderApp({ initialEntries: ["/market"] });
    expect(await screen.findByText("数据源：OKX_PUBLIC_REST")).toBeInTheDocument();
    expect(screen.getAllByTestId("candle")).toHaveLength(60);
    expect(screen.getAllByTestId("candle")[0].querySelector("rect")).toHaveAttribute("fill", "#37c98a");
    expect(screen.getAllByTestId("candle")[1].querySelector("rect")).toHaveAttribute("fill", "#f06470");
    expect(screen.getAllByTestId("candle")[0].querySelector("rect")).toHaveAttribute("data-high", "3.00");
    expect(screen.getByText("后端观测时间：2026-10-30T00:00:00Z")).toBeInTheDocument();
    expect(screen.getByText("最新已收盘价：1.50")).toBeInTheDocument();
    expect(screen.getByText("成交量：9.000")).toBeInTheDocument();
    expect(screen.getByText("收盘时间：2026-10-01T05:00:00.000Z")).toBeInTheDocument();
    expect(screen.getByText(/已收盘历史 K 线/)).toBeInTheDocument();
    expect(screen.queryByText(/实时成交价/)).not.toBeInTheDocument();
  });

  it("GWT-UI01-04: fails closed for 503, network and invalid 200, and manual refresh retries once", async () => {
    seedSession(); let calls = 0;
    server.use(http.get(path, () => { calls++; return calls < 2 ? new HttpResponse(null, { status: 503 }) : HttpResponse.json(payload()); }));
    const user = userEvent.setup(); renderApp({ initialEntries: ["/market"] });
    expect(await screen.findByText("行情暂不可用")).toBeInTheDocument();
    expect(screen.queryByTestId("candle-chart")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "刷新" }));
    expect(await screen.findAllByTestId("candle")).toHaveLength(60);
    expect(calls).toBe(2);
    server.use(http.get(path, () => HttpResponse.json({ ...payload(), items: [candle(1)] })));
    await user.click(screen.getByRole("button", { name: "刷新" }));
    expect(await screen.findByText("数据无法验证")).toBeInTheDocument();
    expect(screen.queryByTestId("candle-chart")).not.toBeInTheDocument();
    server.use(http.get(path, () => HttpResponse.json({ ...payload(), items: Array(60).fill(null) })));
    await user.click(screen.getByRole("button", { name: "刷新" }));
    expect(await screen.findByText("数据无法验证")).toBeInTheDocument();
    expect(screen.queryByTestId("candle-chart")).not.toBeInTheDocument();
    server.use(http.get(path, () => HttpResponse.error()));
    await user.click(screen.getByRole("button", { name: "刷新" }));
    expect(await screen.findByText("网络连接失败")).toBeInTheDocument();
    expect(screen.queryByTestId("candle-chart")).not.toBeInTheDocument();
  });

  it("GWT-UI01-05: a protected 401 clears the session and returns to Login", async () => {
    seedSession(); server.use(http.get(path, () => new HttpResponse(null, { status: 401 })));
    renderApp({ initialEntries: ["/market"] });
    expect(await screen.findByRole("heading", { name: "登录" })).toBeInTheDocument();
    expect(sessionStorage.length).toBe(0);
  });

  it("GWT-UI01-04: a late response for the prior selection cannot replace the current chart", async () => {
    seedSession(); let release!: () => void;
    const waiting = new Promise<void>((resolve) => { release = resolve; });
    server.use(http.get(path, async ({ request }) => {
      const instrument = new URL(request.url).searchParams.get("instrument_id")!;
      if (instrument === "BTC-USDT") await waiting;
      const response = payload(instrument);
      if (instrument === "ETH-USDT") Object.assign(response.items[59], { open: "9.00", high: "10.00", low: "8.00", close: "9.99" });
      return HttpResponse.json(response);
    }));
    const user = userEvent.setup(); renderApp({ initialEntries: ["/market"] });
    expect(await screen.findByText("行情加载中…")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("币种"), "ETH-USDT");
    expect(await screen.findByTestId("candle-chart")).toBeInTheDocument();
    expect(screen.getByText("ETH-USDT")).toBeInTheDocument();
    expect(screen.getAllByTestId("candle")[59].querySelector("rect")).toHaveAttribute("data-close", "9.99");
    release();
    await waitFor(() => expect(screen.getByText("ETH-USDT")).toBeInTheDocument());
    expect(screen.getByTestId("candle-chart")).toBeInTheDocument();
    expect(screen.getAllByTestId("candle")[59].querySelector("rect")).toHaveAttribute("data-close", "9.99");
  });

  it("GWT-UI01-04: rejects gaps, wrong candle duration and timestamps outside the Date range", async () => {
    const valid = payload().items;
    const shift = 8_640_000_000_000_000 + periodMs["5m"] - firstOpen;
    const invalid = [
      valid.map((c, i) => ({ ...c, open_time_ms: firstOpen + i, close_time_ms: firstOpen + i + periodMs["5m"] })),
      valid.map((c, i) => ({ ...c, open_time_ms: firstOpen + i * 60_000, close_time_ms: firstOpen + i * 60_000 + periodMs["5m"] })),
      valid.map((c) => ({ ...c, open_time_ms: c.open_time_ms + 1, close_time_ms: c.close_time_ms + 1 })),
      valid.map((c) => ({ ...c, close_time_ms: c.close_time_ms + 1 })),
      valid.map((c) => ({ ...c, open_time_ms: c.open_time_ms + shift, close_time_ms: c.close_time_ms + shift })),
    ];
    for (const items of invalid) {
      seedSession();
      server.use(http.get(path, () => HttpResponse.json({ ...payload(), items })));
      const app = renderApp({ initialEntries: ["/market"] });
      expect(await screen.findByText("数据无法验证")).toBeInTheDocument();
      expect(screen.queryByTestId("candle-chart")).not.toBeInTheDocument();
      app.unmount();
    }
  });

  it("GWT-UI01-04: rejects continuous aligned candles containing non-positive timestamps", async () => {
    seedSession();
    const step = periodMs["5m"];
    const items = payload().items.map((c, i) => ({
      ...c,
      open_time_ms: (i - 30) * step,
      close_time_ms: (i - 29) * step,
    }));
    server.use(http.get(path, () => HttpResponse.json({ ...payload(), items })));

    renderApp({ initialEntries: ["/market"] });
    expect(await screen.findByText("数据无法验证")).toBeInTheDocument();
    expect(screen.queryByTestId("candle-chart")).not.toBeInTheDocument();
  });
});
