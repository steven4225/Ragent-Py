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
    <section className="border border-slate-900 bg-white">
      <div className="border-b border-slate-200 bg-[#fcfaf4] px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          取舍对比
        </p>
        <h3 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-slate-950">
          解释为什么它应该赢。
        </h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          这一区域的任务是为推荐结论提供证据，不是一次性把所有参数都砸给你。
        </p>
      </div>

      {hasHighlights ? (
        <div className="overflow-x-auto border-b border-slate-200">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  维度
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  主推荐
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  替代项
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  顾问判断
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
          先让主推荐和一个挑战者正面对比，真正的取舍才会浮出来。
        </div>
      )}

      <div className="px-4 py-4">
        {hasSpecTable && compareBlock ? (
          <SpecCompareTable block={compareBlock} />
        ) : (
          <p className="text-sm leading-6 text-slate-600">
            更完整的规格表会留在下面，只有当商品进入主动对比时才会出现。
          </p>
        )}
      </div>
    </section>
  );
}
