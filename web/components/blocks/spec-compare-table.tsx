import type { SpecCompareBlock } from "@/lib/contracts/ecommerce-blocks";

const CATEGORY_TONE: Record<string, string> = {
  laptop: "bg-sky-100 text-sky-800",
  phone: "bg-violet-100 text-violet-800",
  tablet: "bg-emerald-100 text-emerald-800",
  earbuds: "bg-amber-100 text-amber-800",
  monitor: "bg-slate-200 text-slate-800",
};

function categoryTone(category: string): string {
  return CATEGORY_TONE[category] ?? "bg-slate-100 text-slate-700";
}

export function SpecCompareTable({ block }: { block: SpecCompareBlock }) {
  if (block.columns.length === 0) {
    return null;
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm text-slate-800">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 align-bottom">
              <th className="w-32 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Spec
              </th>
              {block.columns.map((column) => (
                <th key={column.product_id} className="px-4 py-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                      {column.brand}
                    </span>
                    <span className="text-sm font-semibold text-slate-950">
                      {column.name}
                    </span>
                    <span
                      className={`inline-flex w-fit items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${categoryTone(column.category)}`}
                    >
                      {column.category}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row) => (
              <tr key={row.label} className="border-b border-slate-100 last:border-b-0">
                <th scope="row" className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">
                  {row.label}
                </th>
                {row.values.map((value, columnIndex) => {
                  const isPlaceholder = value === block.placeholder;
                  const isPriceRow = row.label === "Price";
                  return (
                    <td
                      key={`${row.label}:${columnIndex}`}
                      className={[
                        "px-4 py-3",
                        isPlaceholder ? "text-slate-300" : "text-slate-800",
                        isPriceRow && !isPlaceholder ? "font-semibold text-slate-950" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {value}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
