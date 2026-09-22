export default function ScoreGauge({ score, label = "match" }) {
  const clamped = Math.max(0, Math.min(100, Number(score) || 0));
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const tone =
    clamped >= 75 ? "text-emerald-600" : clamped >= 50 ? "text-amber-600" : "text-rose-600";
  const stroke =
    clamped >= 75 ? "stroke-emerald-500" : clamped >= 50 ? "stroke-amber-500" : "stroke-rose-500";

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative h-36 w-36">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 128 128" aria-hidden="true">
          <circle
            cx="64"
            cy="64"
            r={radius}
            fill="none"
            className="stroke-slate-200"
            strokeWidth="10"
          />
          <circle
            cx="64"
            cy="64"
            r={radius}
            fill="none"
            className={stroke}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-semibold tracking-tight ${tone}`}>{clamped}</span>
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            {label}
          </span>
        </div>
      </div>
      <p className="text-sm text-slate-500">Overall fit against this role</p>
    </div>
  );
}
