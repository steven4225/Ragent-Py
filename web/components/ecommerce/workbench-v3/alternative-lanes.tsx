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
    <section className="border border-slate-900 bg-white">
      <div className="border-b border-slate-200 bg-[#f4efe3] px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          替代路线
        </p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          两条有意识地挑战主推荐的路线，但不重新把整次搜索推倒重来。
        </p>
      </div>

      <div className="grid gap-0 xl:grid-cols-2">
        {lanes.map((lane, index) => (
          <article
            key={lane.lane}
            className={[
              "grid gap-4 px-4 py-5 xl:px-5",
              index === 0 ? "border-b border-slate-200 xl:border-b-0 xl:border-r" : "",
            ].join(" ")}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  路线 {index + 1}
                </p>
                <p className="mt-2 text-sm font-medium text-slate-500">{lane.lane}</p>
              </div>
              <button
                type="button"
                onClick={() => onChooseLane?.(lane)}
                className="border border-slate-900 bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition-colors duration-150 hover:bg-slate-800"
              >
                加入对比
              </button>
            </div>

            <div className="min-w-0">
              <h3 className="text-2xl font-semibold tracking-[-0.03em] text-slate-950">
                {lane.block?.name ?? "替代项待定"}
              </h3>
              <p className="mt-2 text-sm text-slate-600">
                {lane.block
                  ? `${lane.block.brand} / ${lane.block.category} / $${lane.block.price_usd.toLocaleString("en-US")}`
                  : "在候选列表成型之前，这里还不会出现可信替代项。"}
              </p>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-700">{lane.why}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
