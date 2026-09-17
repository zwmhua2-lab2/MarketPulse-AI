/**
 * The route table.
 *
 * UI-V1-D01 §5 freezes the top-level product information architecture to exactly
 * five pages, and explicitly gives AI no top-level page. This module is the single
 * declaration of that table so the router and the product shell cannot drift apart.
 */

export interface ProductRoute {
  /** Top-level path, e.g. `/market`. */
  readonly path: string;
  /** Simplified-Chinese page title. */
  readonly title: string;
  /** The batch that will replace the Foundation placeholder with the real page. */
  readonly ownerBatch: string;
}

/** Exactly five top-level product routes. There is deliberately no `/ai` route. */
export const PRODUCT_ROUTES: readonly ProductRoute[] = [
  { path: "/overview", title: "总览", ownerBatch: "UI-I05" },
  { path: "/market", title: "市场与机会", ownerBatch: "UI-I02" },
  { path: "/research", title: "策略研究", ownerBatch: "UI-I04" },
  { path: "/trading", title: "交易与仓位", ownerBatch: "UI-I03" },
  { path: "/system", title: "系统", ownerBatch: "UI-I01" },
];

/**
 * The Auth Shell route. It is part of UI V1 but is not a sixth product page
 * (UI-V1-D01 §25).
 */
export const LOGIN_ROUTE = "/login";

/** Where `/` and any unknown path inside the product shell resolve to. */
export const DEFAULT_PRODUCT_ROUTE = "/overview";
