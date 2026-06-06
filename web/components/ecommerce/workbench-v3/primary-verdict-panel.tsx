import type { PrimaryVerdict } from "@/lib/ecommerce/workbench-v3-view-model";

type PrimaryVerdictPanelProps = {
  verdict: PrimaryVerdict;
  onInspectCompare?: () => void;
  onInspectAlternatives?: () => void;
};

export function PrimaryVerdictPanel({
  verdict,
  onInspectCompare,
  onInspectAlternatives,
}: PrimaryVerdictPanelProps) {
  const winner = verdict.winner;
  const leadSpecs = winner?.specs.slice(0, 4) ?? [];

  return (
    <section className="border border-slate-900 bg-[#fcfaf4]">
      <div className="grid gap-0 xl:grid-cols-[140px_minmax(0,1fr)]">
        <div className="border-b border-slate-200 bg-[#f1ebdf] px-5 py-5 xl:border-b-0 xl:border-r xl:px-6 xl:py-8">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
            01
          </p>
          <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
            主推荐结论
          </p>
          <p className="mt-4 text-sm leading-6 text-slate-700">
            在进入更深的对比之前，页面必须先给出一个清晰的推荐对象。
          </p>
        </div>

        <div className="min-w-0">
          <div className="border-b border-slate-200 px-5 py-6 xl:px-8 xl:py-8">
            <div className="grid gap-8 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                  当前推荐
                </p>
                <h2 className="mt-3 max-w-4xl text-5xl font-semibold tracking-[-0.05em] text-slate-950 xl:text-[5.2rem] xl:leading-[0.94]">
                  {winner ? winner.name : "还没有形成主推荐"}
                </h2>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-700">
                  {winner
                    ? `${winner.brand} / ${winner.category} / $${winner.price_usd.toLocaleString("en-US")} / ${winner.release_year}`
                    : "先提交需求，或者放宽限制，让顾问能提出一个可信的一号选择。"}
                </p>
              </div>

              <div className="border-l border-slate-200 pl-0 xl:pl-6">
                <div className="grid gap-5">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                      不适合谁
                    </p>
                    <p className="mt-3 text-sm leading-7 text-slate-900">{verdict.notIdealFor}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                      主要代价
                    </p>
                    <p className="mt-3 text-sm leading-7 text-slate-900">{verdict.mainTradeoff}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 max-w-4xl border-l-2 border-slate-900 pl-4 text-[1.04rem] leading-8 text-slate-800">
              <p>{verdict.why}</p>
            </div>
          </div>

          <div className="grid gap-0 border-b border-slate-200 md:grid-cols-4">
            {leadSpecs.length > 0 ? (
              leadSpecs.map((spec) => (
                <div
                  key={spec.label}
                  className="border-b border-slate-200 px-5 py-4 last:border-b-0 md:border-b-0 md:border-r last:md:border-r-0 xl:px-8"
                >
                  <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    {spec.label}
                  </p>
                  <p className="mt-2 text-sm font-medium text-slate-950">{spec.value}</p>
                </div>
              ))
            ) : (
              <div className="px-5 py-4 text-sm text-slate-600 xl:px-8">
                只有在形成可信主推荐后，这条核心规格带才会出现。
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-3 px-5 py-4 xl:px-8">
            <button
              type="button"
              onClick={onInspectCompare}
              className="border border-slate-950 bg-slate-950 px-3 py-2 text-sm font-semibold text-white transition-colors duration-150 hover:bg-slate-800"
            >
              查看对比
            </button>
            <button
              type="button"
              onClick={onInspectAlternatives}
              className="border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition-colors duration-150 hover:border-slate-500"
            >
              看替代路线
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
