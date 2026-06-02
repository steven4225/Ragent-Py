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
    <section className="border border-slate-950 bg-white">
      <div className="grid gap-0 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
        <div className="border-b border-slate-200 px-5 py-5 xl:border-b-0 xl:border-r">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Primary verdict
          </p>
          <div className="mt-4">
            <p className="text-sm font-medium text-slate-600">Current recommendation</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
              {winner ? winner.name : "No winner framed yet"}
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              {winner
                ? `${winner.brand} • ${winner.category} • $${winner.price_usd.toLocaleString("en-US")}`
                : "Run a brief or relax the constraints so the advisor can name a credible top pick."}
            </p>
          </div>

          <div className="mt-5 max-w-3xl text-sm leading-7 text-slate-700">
            <p>{verdict.why}</p>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onInspectCompare}
              className="border border-slate-950 bg-slate-950 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              Inspect compare
            </button>
            <button
              type="button"
              onClick={onInspectAlternatives}
              className="border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-950 hover:text-slate-950"
            >
              Review alternatives
            </button>
          </div>
        </div>

        <div className="grid gap-0 md:grid-cols-2 xl:grid-cols-1">
          <div className="border-b border-slate-200 px-5 py-4 md:border-r xl:border-r-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Not ideal for
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-900">{verdict.notIdealFor}</p>
          </div>
          <div className="px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Main trade-off
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-900">{verdict.mainTradeoff}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
