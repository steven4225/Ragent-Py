import type { AdvisorState } from "@/components/ecommerce/workbench/types";
import type { DecisionMemo } from "@/lib/ecommerce/workbench-v3-view-model";

type DecisionMemoPanelProps = {
  memo: DecisionMemo;
  advisor?: AdvisorState | null;
};

export function DecisionMemoPanel({
  memo,
  advisor,
}: DecisionMemoPanelProps) {
  return (
    <aside className="border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Decision memo
        </p>
        <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
          A rational close, not a chat transcript.
        </h3>
      </div>

      <div className="divide-y divide-slate-200">
        <section className="px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Recommendation
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-900">{memo.recommendation}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Buy if
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-900">{memo.buyIf}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Avoid if
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-900">{memo.avoidIf}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Main trade-off
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-900">{memo.tradeOff}</p>
        </section>
        <section className="px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Revisit when
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-900">{memo.revisitWhen}</p>
        </section>
      </div>

      {advisor ? (
        <footer className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-500">
          Advisor state: {advisor.status}
          {advisor.provider ? ` • ${advisor.provider}` : ""}
          {advisor.model ? ` • ${advisor.model}` : ""}
        </footer>
      ) : null}
    </aside>
  );
}
