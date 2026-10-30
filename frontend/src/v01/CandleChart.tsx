import type { components } from "../api/generated";

type Candle = components["schemas"]["MarketCandleItem"];

export function CandleChart({ items }: { items: Candle[] }) {
  const values = items.flatMap((c) => [Number(c.high), Number(c.low)]);
  const min = Math.min(...values), span = Math.max(...values) - min || 1;
  const y = (price: string) => 160 - ((Number(price) - min) / span) * 140;
  return <svg className="candle-chart" data-testid="candle-chart" viewBox="0 0 600 180" role="img" aria-label="60 根已收盘 K 线">
    {items.map((c, i) => {
      const x = i * 10 + 1, rising = Number(c.close) >= Number(c.open), color = rising ? "#37c98a" : "#f06470";
      const top = Math.min(y(c.open), y(c.close)), height = Math.max(1, Math.abs(y(c.open) - y(c.close)));
      return <g data-testid="candle" key={c.open_time_ms}>
        <line x1={x + 3} x2={x + 3} y1={y(c.high)} y2={y(c.low)} stroke={color} />
        <rect x={x} y={top} width="6" height={height} fill={color} data-open={c.open} data-high={c.high} data-low={c.low} data-close={c.close} />
      </g>;
    })}
  </svg>;
}
