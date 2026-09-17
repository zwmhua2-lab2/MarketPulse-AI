/**
 * Placeholder body for a product page whose business UI is not built yet.
 *
 * UI-F01 is Foundation only: every product route renders this. It performs no
 * fetching and renders no production widget, chart or table, so that no future
 * Product Read API is implied before its contract exists (UI-F01 §6).
 */

export interface FoundationPlaceholderProps {
  /** Page title, e.g. `市场与机会`. */
  readonly title: string;
  /** Which batch will build the real page, e.g. `UI-I02`. */
  readonly ownerBatch: string;
}

export function FoundationPlaceholder({ title, ownerBatch }: FoundationPlaceholderProps) {
  return (
    <section className="foundation-placeholder" aria-labelledby="foundation-placeholder-title">
      <h1 id="foundation-placeholder-title">{title}</h1>
      <p>
        {title} — 将在 {ownerBatch} 实现
      </p>
    </section>
  );
}
