import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { components } from "../api/generated";
import { HttpError, NetworkError } from "../api/errors";
import { requestData } from "../api/transport";
import { useApiClient } from "../auth/AuthSessionProvider";
import { CandleChart } from "./CandleChart";
import "./market.css";

type Instrument = "BTC-USDT" | "ETH-USDT";
type Bar = "5m" | "15m" | "1h";
type Response = components["schemas"]["MarketCandleResponse"];
const bars: Bar[] = ["5m", "15m", "1h"];
const periodMs: Record<Bar, number> = { "5m": 300_000, "15m": 900_000, "1h": 3_600_000 };
const validTimestamp = (value: unknown) => typeof value === "number" && Number.isSafeInteger(value) && value > 0 && Number.isFinite(new Date(value).getTime());

function valid(value: unknown, instrument: Instrument, bar: Bar): value is Response {
  if (!value || typeof value !== "object") return false;
  const data = value as Partial<Response>;
  return data.instrument_id === instrument && data.bar === bar && data.source === "OKX_PUBLIC_REST" &&
    data.data_quality === "FRESH" && typeof data.observed_at === "string" && Number.isFinite(Date.parse(data.observed_at)) &&
    Array.isArray(data.items) && data.items.length === 60 && data.items.every((item, i, items) => {
      if (!item || typeof item !== "object") return false;
      const c = item as Partial<Response["items"][number]>;
      const prices = [c.open, c.high, c.low, c.close];
      const step = periodMs[bar];
      return c.confirmed === true && prices.every((v) => typeof v === "string" && /^\d+(?:\.\d+)?$/.test(v) && Number.isFinite(Number(v)) && Number(v) > 0) &&
        typeof c.volume === "string" && /^\d+(?:\.\d+)?$/.test(c.volume) && Number.isFinite(Number(c.volume)) &&
        validTimestamp(c.open_time_ms) && validTimestamp(c.close_time_ms) && c.open_time_ms! % step === 0 && c.close_time_ms! - c.open_time_ms! === step &&
        Number(c.high) >= Math.max(Number(c.open), Number(c.close), Number(c.low)) && Number(c.low) <= Math.min(Number(c.open), Number(c.close)) &&
        (i === 0 || c.open_time_ms === Number(items[i - 1].open_time_ms) + step);
    });
}

export function MarketPage() {
  const client = useApiClient();
  const [denied, setDenied] = useState(false);
  const [instrument, setInstrument] = useState<Instrument>("BTC-USDT");
  const [bar, setBar] = useState<Bar>("5m");
  const query = useQuery({
    queryKey: ["market-candles", instrument, bar], retry: false, refetchOnReconnect: false, enabled: !denied,
    queryFn: () => requestData(async () => {
      const result = await client.GET("/api/v1/product/market-candles", { params: { query: { instrument_id: instrument, bar } } });
      if (result.response.status === 401) setDenied(true);
      return result;
    }),
  });
  const data = query.data && valid(query.data, instrument, bar) ? query.data : undefined;
  const error = denied ? "当前模式需登录/无权读取行情" : query.error instanceof HttpError && query.error.status === 503 ? "行情暂不可用"
    : query.error instanceof NetworkError ? "网络连接失败"
    : query.error ? "行情读取失败，请手动重试" : "数据无法验证";

  return <section className="market-page">
    <p className="eyebrow">MARKET DATA · READ ONLY</p><h1>市场与机会</h1>
    <div className="market-controls">
      <label>币种<select aria-label="币种" value={instrument} onChange={(e) => setInstrument(e.target.value as Instrument)}>
        <option>BTC-USDT</option><option>ETH-USDT</option></select></label>
      <label>周期<select aria-label="周期" value={bar} onChange={(e) => setBar(e.target.value as Bar)}>
        {bars.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching || denied}>刷新</button>
    </div>
    {denied ? <p role="alert">{error}</p> : query.isPending ? <p role="status">行情加载中…</p> : query.isError || !data ? <p role="alert">{error}</p> : <>
      <section className="market-facts" aria-label="行情事实">
        <span>数据源：{data.source}</span><span>后端观测时间：{data.observed_at}</span>
        <span>最新已收盘价：{data.items.at(-1)!.close}</span>
        <span>开盘时间：{new Date(data.items.at(-1)!.open_time_ms).toISOString()}</span>
        <span>收盘时间：{new Date(data.items.at(-1)!.close_time_ms).toISOString()}</span>
        <span>成交量：{data.items.at(-1)!.volume}</span>
      </section><CandleChart items={data.items} />
    </>}
    <p>仅为已收盘历史 K 线，不代表实时买卖报价或交易建议。</p>
  </section>;
}
