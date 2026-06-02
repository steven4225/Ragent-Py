type ReferenceBrief = {
  id: string;
  title: string;
  subtitle: string;
};

type AdvisorBriefBarProps = {
  brief: string;
  budgetLabel?: string;
  useCase?: string;
  mustHaves?: string[];
  niceToHaves?: string[];
  warnings?: string[];
  disabled?: boolean;
  dataModeLabel?: string;
  referenceBriefs?: ReferenceBrief[];
  activeReferenceId?: string | null;
  onBriefChange?: (value: string) => void;
  onSubmit?: () => void;
  onPickReference?: (id: string) => void;
};

function renderList(values: string[] | undefined, fallback: string): string {
  if (!values || values.length === 0) return fallback;
  return values.join(" / ");
}

export function AdvisorBriefBar({
  brief,
  budgetLabel = "Flexible",
  useCase = "General purchase decision",
  mustHaves,
  niceToHaves,
  warnings,
  disabled = false,
  dataModeLabel,
  referenceBriefs = [],
  activeReferenceId = null,
  onBriefChange,
  onSubmit,
  onPickReference,
}: AdvisorBriefBarProps) {
  return (
    <section className="border border-slate-300 bg-[#fbf8f1]">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Shopping brief
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            State the need once. The page should narrow the field and name one credible pick before
            it asks you to compare.
          </p>
        </div>
        {dataModeLabel ? (
          <div className="inline-flex items-center border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
            {dataModeLabel}
          </div>
        ) : null}
      </div>

      <form
        className="px-4 py-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit?.();
        }}
      >
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
          <div className="min-w-0 flex-1 border border-slate-300 bg-white">
            <input
              value={brief}
              onChange={(event) => onBriefChange?.(event.target.value)}
              placeholder="Laptop under $1500 for coding, calls, and light gaming"
              className="min-h-12 w-full bg-transparent px-3 text-sm text-slate-950 placeholder:text-slate-400 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={disabled}
            className="min-h-12 border border-slate-950 bg-slate-950 px-4 text-sm font-semibold text-white transition-colors duration-150 hover:bg-slate-800 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-200 disabled:text-slate-500"
          >
            Build recommendation
          </button>
        </div>

        {referenceBriefs.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="self-center text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">
              Reference briefs
            </span>
            {referenceBriefs.map((reference) => {
              const isActive = reference.id === activeReferenceId;
              return (
                <button
                  key={reference.id}
                  type="button"
                  onClick={() => onPickReference?.(reference.id)}
                  className={[
                    "border px-3 py-1.5 text-left transition-colors duration-150",
                    isActive
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-400",
                  ].join(" ")}
                >
                  <span className="block text-xs font-semibold">{reference.title}</span>
                  <span
                    className={[
                      "mt-1 block text-[10px]",
                      isActive ? "text-slate-200" : "text-slate-500",
                    ].join(" ")}
                  >
                    {reference.subtitle}
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}
      </form>

      <div className="grid gap-0 border-t border-slate-200 lg:grid-cols-[170px_minmax(0,1.1fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <section className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Budget
          </p>
          <p className="mt-1 text-sm text-slate-950">{budgetLabel}</p>
          <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Use case
          </p>
          <p className="mt-1 text-sm text-slate-950">{useCase}</p>
        </section>

        <section className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Must-have
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">
            {renderList(mustHaves, "No hard constraints extracted yet.")}
          </p>
        </section>

        <section className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Nice-to-have
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">
            {renderList(niceToHaves, "No secondary preferences extracted yet.")}
          </p>
        </section>

        <section className="px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Constraint tension
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">
            {renderList(warnings, "No obvious tension detected in the current brief.")}
          </p>
        </section>
      </div>
    </section>
  );
}
