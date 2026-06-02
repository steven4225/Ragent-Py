import type { ReactNode } from "react";

type CatalogDrawerProps = {
  open: boolean;
  onToggle: () => void;
  summary?: string;
  children?: ReactNode;
};

export function CatalogDrawer({
  open,
  onToggle,
  summary = "Open the deeper catalog only after the recommendation and compare layers are clear.",
  children,
}: CatalogDrawerProps) {
  return (
    <section className="border border-slate-200 bg-white">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-4 py-4 text-left transition-colors duration-150 hover:bg-slate-50"
        aria-expanded={open}
      >
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Catalog layer
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{summary}</p>
        </div>
        <span className="border border-slate-300 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-700">
          {open ? "Collapse" : "Expand"}
        </span>
      </button>

      <div
        className={[
          "grid overflow-hidden transition-[grid-template-rows] duration-200 ease-out",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        ].join(" ")}
      >
        <div className="min-h-0">
          <div className="border-t border-slate-200 px-4 py-4">
            {children ?? (
              <p className="text-sm leading-6 text-slate-600">
                The broader product pool, richer filters, and fuller spec views plug in here.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
