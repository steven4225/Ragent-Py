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
  budgetLabel = "弹性预算",
  useCase = "一般购买决策",
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
    <section className="bg-[#fcfaf4]">
      <div className="flex flex-col gap-2 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            购买需求
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            只要把需求说明白一次，这个页面就该先给出一个可信的一号推荐，而不是先让你做更多操作。
          </p>
        </div>
        {dataModeLabel ? (
          <div className="inline-flex items-center border border-slate-300 bg-white px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
            {dataModeLabel}
          </div>
        ) : null}
      </div>

      <form
        className="border-b border-slate-200 px-4 py-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit?.();
        }}
      >
        <div className="flex flex-col gap-2 xl:flex-row xl:items-center">
          <div className="min-w-0 flex-1 border border-slate-900 bg-white">
            <input
              value={brief}
              onChange={(event) => onBriefChange?.(event.target.value)}
              placeholder="例如：1500 美元以内，适合写代码、开会和轻度游戏的笔记本"
              className="min-h-12 w-full bg-transparent px-4 text-sm text-slate-950 placeholder:text-slate-400 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={disabled}
            className="min-h-12 border border-slate-950 bg-slate-950 px-5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-slate-800 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-200 disabled:text-slate-500"
          >
            生成建议
          </button>
        </div>

        {referenceBriefs.length > 0 ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="self-center text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">
              参考任务
            </span>
            {referenceBriefs.map((reference) => {
              const isActive = reference.id === activeReferenceId;
              return (
                <button
                  key={reference.id}
                  type="button"
                  onClick={() => onPickReference?.(reference.id)}
                  className={[
                    "border px-3 py-1.5 text-left text-xs font-semibold transition-colors duration-150",
                    isActive
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-400",
                  ].join(" ")}
                >
                  <span className="block">{reference.title}</span>
                </button>
              );
            })}
          </div>
        ) : null}
      </form>

      <div className="grid gap-0 lg:grid-cols-[170px_minmax(0,1.1fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <section className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            预算
          </p>
          <p className="mt-1 text-sm text-slate-950">{budgetLabel}</p>
          <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            使用场景
          </p>
          <p className="mt-1 text-sm text-slate-950">{useCase}</p>
        </section>

        <section className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            必要条件
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">
            {renderList(mustHaves, "还没有提取出明确的硬约束。")}
          </p>
        </section>

        <section className="border-b border-slate-200 px-4 py-3 lg:border-b-0 lg:border-r">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            加分项
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">
            {renderList(niceToHaves, "还没有提取出明确的次级偏好。")}
          </p>
        </section>

        <section className="px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            约束冲突
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-950">
            {renderList(warnings, "当前需求里没有明显的约束冲突。")}
          </p>
        </section>
      </div>
    </section>
  );
}
