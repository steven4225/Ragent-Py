import type { DecisionMemo } from "@/lib/ecommerce/workbench-v3-view-model";

type DecisionMemoPanelProps = {
  memo: DecisionMemo;
};

export function DecisionMemoPanel({
  memo,
}: DecisionMemoPanelProps) {
  return (
    <aside className="border border-slate-900 bg-[#fffdf8]">
      <div className="border-b border-slate-200 bg-[#efe7d8] px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          购买意见
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          把推荐结论压缩成一份简短、克制、可执行的意见书。
        </p>
      </div>

      <div className="px-4 py-4">
        <div className="border border-slate-900 bg-white px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            摘要
          </p>
          <p className="mt-3 text-[0.98rem] leading-8 text-slate-900">{memo.recommendation}</p>
        </div>
      </div>

      <div className="divide-y divide-slate-200">
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            适合买它
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-900">{memo.buyIf}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            不适合买它
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-900">{memo.avoidIf}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            主要代价
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-900">{memo.tradeOff}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            如果优先级变化
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-900">{memo.revisitWhen}</p>
        </section>
      </div>
    </aside>
  );
}
