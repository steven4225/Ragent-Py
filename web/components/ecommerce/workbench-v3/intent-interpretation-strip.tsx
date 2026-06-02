import type { IntentInterpretation } from "@/lib/ecommerce/workbench-v3-view-model";

export function IntentInterpretationStrip({
  buyingTask,
  priorityLine,
  advisorPath,
  riskNote,
}: IntentInterpretation) {
  return (
    <section className="border border-slate-200 bg-[#f7f3ea]">
      <div className="grid gap-0 lg:grid-cols-4">
        <div className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Buying task
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">{buyingTask}</p>
        </div>
        <div className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Priority
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">{priorityLine}</p>
        </div>
        <div className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Advisor path
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">{advisorPath}</p>
        </div>
        <div className="px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Risk note
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">{riskNote}</p>
        </div>
      </div>
    </section>
  );
}
