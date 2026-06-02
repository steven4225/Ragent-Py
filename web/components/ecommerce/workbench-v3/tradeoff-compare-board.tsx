import { SpecCompareTable } from "@/components/blocks/spec-compare-table";
import type { SpecCompareBlock } from "@/lib/contracts/ecommerce-blocks";
import type { CompareHighlightRow } from "@/lib/ecommerce/workbench-v3-view-model";

type TradeoffCompareBoardProps = {
  highlights: CompareHighlightRow[];
  compareBlock: SpecCompareBlock | null;
};

export function TradeoffCompareBoard({
  highlights,
  compareBlock,
}: TradeoffCompareBoardProps) {
  const hasHighlights = highlights.length > 0;
  const hasSpecTable = Boolean(compareBlock?.columns.length);

  return (
    <section className="border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Trade-off compare
        </p>
        <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
          Justify the verdict before opening the full spec wall.
        </h3>
      </div>

      {hasHighlights ? (
        <div className="overflow-x-auto border-b border-slate-200">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Dimension
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Primary
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Alternative
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Advisor read
                </th>
              </tr>
            </thead>
            <tbody>
              {highlights.map((row) => (
                <tr key={row.label} className="border-b border-slate-100 align-top last:border-b-0">
                  <th className="px-4 py-4 text-sm font-semibold text-slate-950">{row.label}</th>
                  <td className="px-4 py-4 text-sm text-slate-700">{row.primaryValue}</td>
                  <td className="px-4 py-4 text-sm text-slate-700">{row.alternativeValue}</td>
                  <td className="px-4 py-4 text-sm leading-6 text-slate-700">{row.verdict}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="border-b border-slate-200 px-4 py-5 text-sm leading-6 text-slate-600">
          Compare two shortlisted products to surface the real trade-off.
        </div>
      )}

      <div className="px-4 py-4">
        {hasSpecTable && compareBlock ? (
          <SpecCompareTable block={compareBlock} />
        ) : (
          <p className="text-sm leading-6 text-slate-600">
            The deeper spec table stays below the decision summary and only appears after products
            are actively compared.
          </p>
        )}
      </div>
    </section>
  );
}
