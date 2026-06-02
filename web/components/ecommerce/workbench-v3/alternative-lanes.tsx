import type { AlternativeLane } from "@/lib/ecommerce/workbench-v3-view-model";

type AlternativeLanesProps = {
  lanes: AlternativeLane[];
  onChooseLane?: (lane: AlternativeLane) => void;
};

export function AlternativeLanes({
  lanes,
  onChooseLane,
}: AlternativeLanesProps) {
  return (
    <section className="border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Alternative lanes
        </p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Two deliberate ways to challenge the current recommendation without reopening the whole
          catalog from zero.
        </p>
      </div>

      <div className="divide-y divide-slate-200">
        {lanes.map((lane) => (
          <article
            key={lane.lane}
            className="grid gap-4 px-4 py-4 lg:grid-cols-[150px_minmax(0,1fr)_auto] lg:items-center"
          >
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {lane.lane}
              </p>
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-semibold tracking-tight text-slate-950 sm:text-lg">
                {lane.block?.name ?? "Alternative pending"}
              </h3>
              <p className="mt-1 text-sm text-slate-600">
                {lane.block
                  ? `${lane.block.brand} / ${lane.block.category} / $${lane.block.price_usd.toLocaleString("en-US")}`
                  : "No alternative is available until the shortlist fills in."}
              </p>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{lane.why}</p>
            </div>
            <div>
              <button
                type="button"
                onClick={() => onChooseLane?.(lane)}
                className="border border-slate-300 bg-[#fbf9f3] px-3 py-2 text-sm font-semibold text-slate-700 transition-colors duration-150 hover:border-slate-500"
              >
                Compare
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
