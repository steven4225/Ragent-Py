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

  return (
    <section className="border border-slate-900 bg-[#fcfaf4] shadow-[0_1px_0_rgba(15,23,42,0.04)]">
      <div className="grid gap-0 xl:grid-cols-[minmax(0,1.75fr)_minmax(320px,0.82fr)]">
        <div className="border-b border-slate-200 px-5 py-6 xl:border-b-0 xl:border-r xl:px-8 xl:py-9">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
            Primary verdict
          </p>
          <p className="mt-5 text-sm font-medium text-slate-500">More suitable right now</p>
          <h2 className="mt-2 max-w-4xl text-4xl font-semibold tracking-tight text-slate-950 xl:text-[3.7rem] xl:leading-[1.01]">
            {winner ? winner.name : "No winner framed yet"}
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-700">
            {winner
              ? `${winner.brand} / ${winner.category} / $${winner.price_usd.toLocaleString("en-US")} / ${winner.release_year}`
              : "Run a brief or relax the constraints so the advisor can name one credible top pick."}
          </p>

          <div className="mt-8 max-w-3xl border-l-2 border-slate-900 pl-4 text-[1.02rem] leading-8 text-slate-800">
            <p>{verdict.why}</p>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onInspectCompare}
              className="border border-slate-950 bg-slate-950 px-3 py-2 text-sm font-semibold text-white transition-colors duration-150 hover:bg-slate-800"
            >
              Inspect compare
            </button>
            <button
              type="button"
              onClick={onInspectAlternatives}
              className="border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition-colors duration-150 hover:border-slate-500"
            >
              Review alternatives
            </button>
          </div>
        </div>

        <div className="grid gap-0 bg-white md:grid-cols-2 xl:grid-cols-1">
          <section className="border-b border-slate-200 px-5 py-5 md:border-r xl:border-r-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Not suitable for
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-900">{verdict.notIdealFor}</p>
          </section>
          <section className="px-5 py-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Main trade-off
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-900">{verdict.mainTradeoff}</p>
          </section>
        </div>
      </div>
    </section>
  );
}
