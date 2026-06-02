type AdvisorBriefBarProps = {
  brief: string;
  budgetLabel?: string;
  useCase?: string;
  mustHaves?: string[];
  niceToHaves?: string[];
  disabled?: boolean;
  dataModeLabel?: string;
  onBriefChange?: (value: string) => void;
  onSubmit?: () => void;
};

function renderList(values: string[] | undefined, fallback: string): string {
  if (!values || values.length === 0) {
    return fallback;
  }
  return values.join(" • ");
}

export function AdvisorBriefBar({
  brief,
  budgetLabel = "Flexible",
  useCase = "General purchase decision",
  mustHaves,
  niceToHaves,
  disabled = false,
  dataModeLabel,
  onBriefChange,
  onSubmit,
}: AdvisorBriefBarProps) {
  return (
    <section className="border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              Advisor brief
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
              Start with the shopping question, not the product wall.
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Frame the need in plain language. The page should interpret it, make one clear call,
              and only then open deeper compare or catalog layers.
            </p>
          </div>
          {dataModeLabel ? (
            <div className="inline-flex items-center border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600">
              {dataModeLabel}
            </div>
          ) : null}
        </div>
      </div>

      <form
        className="border-b border-slate-200 px-4 py-4 sm:px-5"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit?.();
        }}
      >
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <input
            value={brief}
            onChange={(event) => onBriefChange?.(event.target.value)}
            placeholder="Laptop under $1500 for coding, calls, and light gaming"
            className="min-h-12 min-w-0 flex-1 border border-slate-300 px-3 text-sm text-slate-950 placeholder:text-slate-400 focus:border-slate-950 focus:outline-none"
          />
          <button
            type="submit"
            disabled={disabled}
            className="min-h-12 border border-slate-950 bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-200 disabled:text-slate-500"
          >
            Build recommendation
          </button>
        </div>
      </form>

      <dl className="grid gap-0 md:grid-cols-4">
        <div className="border-b border-slate-200 px-4 py-4 md:border-b-0 md:border-r">
          <dt className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Budget
          </dt>
          <dd className="mt-2 text-sm text-slate-950">{budgetLabel}</dd>
        </div>
        <div className="border-b border-slate-200 px-4 py-4 md:border-b-0 md:border-r">
          <dt className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Use case
          </dt>
          <dd className="mt-2 text-sm text-slate-950">{useCase}</dd>
        </div>
        <div className="border-b border-slate-200 px-4 py-4 md:border-b-0 md:border-r">
          <dt className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Must-have
          </dt>
          <dd className="mt-2 text-sm leading-6 text-slate-950">
            {renderList(mustHaves, "No hard constraints extracted yet.")}
          </dd>
        </div>
        <div className="px-4 py-4">
          <dt className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Nice-to-have
          </dt>
          <dd className="mt-2 text-sm leading-6 text-slate-950">
            {renderList(niceToHaves, "No secondary preferences extracted yet.")}
          </dd>
        </div>
      </dl>
    </section>
  );
}
