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
      <div className="border-b border-slate-200 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Alternative lanes
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Challenge the main pick through two controlled directions instead of reopening the whole
          catalog.
        </p>
      </div>

      <div className="divide-y divide-slate-200">
        {lanes.map((lane) => (
          <article
            key={lane.lane}
            className="grid gap-4 px-4 py-4 lg:grid-cols-[160px_minmax(0,1fr)_auto] lg:items-start"
          >
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {lane.lane}
              </p>
            </div>
            <div className="min-w-0">
              <h3 className="text-lg font-semibold tracking-tight text-slate-950">
                {lane.block?.name ?? "Alternative pending"}
              </h3>
              <p className="mt-1 text-sm text-slate-600">
                {lane.block
                  ? `${lane.block.brand} • ${lane.block.category} • $${lane.block.price_usd.toLocaleString("en-US")}`
                  : "No alternative is available until the shortlist fills in."}
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-700">{lane.why}</p>
            </div>
            <div>
              <button
                type="button"
                onClick={() => onChooseLane?.(lane)}
                className="border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-950 hover:text-slate-950"
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
