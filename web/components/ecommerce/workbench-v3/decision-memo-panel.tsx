import type { DecisionMemo } from "@/lib/ecommerce/workbench-v3-view-model";

type DecisionMemoPanelProps = {
  memo: DecisionMemo;
};

export function DecisionMemoPanel({
  memo,
}: DecisionMemoPanelProps) {
  return (
    <aside className="border border-slate-200 bg-[#fcfaf4]">
      <div className="border-b border-slate-200 px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Decision memo
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          A defended recommendation in plain buying language.
        </p>
      </div>

      <div className="divide-y divide-slate-200">
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Recommendation
          </p>
          <p className="mt-2 text-sm leading-7 text-slate-900">{memo.recommendation}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Buy this if
          </p>
          <p className="mt-2 text-sm leading-7 text-slate-900">{memo.buyIf}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Avoid this if
          </p>
          <p className="mt-2 text-sm leading-7 text-slate-900">{memo.avoidIf}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Main trade-off
          </p>
          <p className="mt-2 text-sm leading-7 text-slate-900">{memo.tradeOff}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            If priorities change
          </p>
          <p className="mt-2 text-sm leading-7 text-slate-900">{memo.revisitWhen}</p>
        </section>
      </div>
    </aside>
  );
}
