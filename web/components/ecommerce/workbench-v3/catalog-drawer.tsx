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
  summary = "只有在主推荐和关键对比都清楚之后，才展开更深的商品池。",
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
            商品池展开层
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{summary}</p>
        </div>
        <span className="border border-slate-300 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-700">
          {open ? "收起" : "展开"}
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
                更宽的商品池、更细的筛选条件和更完整的规格视图会放在这里。
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
