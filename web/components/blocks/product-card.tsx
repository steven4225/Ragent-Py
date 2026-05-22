import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

/**
 * Renderer component for the Python-emitted `product_card` block.
 *
 * Step D goal: deterministic, network-free product cards rendered from
 * a `ProductCardBlock` JSON payload. No image fetching (the
 * `image_url` is a known placeholder), no LLM, no markdown parsing —
 * the layout is intentionally static so future LLM-driven flows can
 * pipe the same block shape through without re-tuning the renderer.
 */

const CATEGORY_COLOR: Record<string, string> = {
  laptop: "bg-indigo-50 text-indigo-700",
  phone: "bg-emerald-50 text-emerald-700",
  tablet: "bg-amber-50 text-amber-700",
  earbuds: "bg-rose-50 text-rose-700",
  monitor: "bg-sky-50 text-sky-700",
};

function formatPrice(priceUsd: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(priceUsd);
}

export function ProductCard({ block }: { block: ProductCardBlock }) {
  const categoryClass = CATEGORY_COLOR[block.category] ?? "bg-slate-100 text-slate-700";
  return (
    <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
            {block.brand}
          </p>
          <h3 className="mt-1 text-base font-semibold leading-snug text-slate-950">
            {block.name}
          </h3>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold capitalize ${categoryClass}`}
        >
          {block.category}
        </span>
      </header>

      <p className="mt-3 text-sm leading-6 text-slate-600">{block.summary}</p>

      <div className="mt-4 flex items-baseline justify-between border-b border-dashed border-slate-200 pb-3">
        <div className="text-2xl font-semibold text-slate-950">
          {formatPrice(block.price_usd)}
        </div>
        <div className="text-xs text-slate-400">Released {block.release_year}</div>
      </div>

      {block.specs.length > 0 && (
        <dl className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
          {block.specs.map((spec) => (
            <div key={spec.label} className="flex flex-col">
              <dt className="text-slate-400">{spec.label}</dt>
              <dd className="font-medium text-slate-700">{spec.value}</dd>
            </div>
          ))}
        </dl>
      )}

      <footer className="mt-auto pt-4 text-[11px] text-slate-400">
        product_id: <code className="font-mono">{block.product_id}</code>
      </footer>
    </article>
  );
}
