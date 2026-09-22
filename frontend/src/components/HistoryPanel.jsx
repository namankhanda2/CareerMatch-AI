import { useEffect, useState } from "react";
import { fetchHistory } from "../api.js";
import Results from "./Results.jsx";

function SummaryRow({ item, onSelect }) {
  const selectedBadge =
    item.source === "compare" ? "Compare" : "Analysis";
  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      className="flex w-full items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left shadow-card hover:border-brand-500"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-ink-900">
          {item.role || "Untitled role"}
        </p>
        <p className="text-xs text-slate-500">
          {selectedBadge} · {item.timestamp?.replace("T", " ").slice(0, 16) ?? ""}
          {item.ats_score != null ? ` · ATS ${item.ats_score}/100` : ""}
        </p>
      </div>
      <div className="text-right">
        <p className="text-lg font-semibold text-brand-600">{item.match_score}</p>
        <p className="text-xs text-slate-400">match</p>
      </div>
    </button>
  );
}

export default function HistoryPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchHistory()
      .then((rows) => {
        if (cancelled) return;
        setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Could not load history.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="py-8 text-center text-sm text-slate-500">Loading history…</p>;
  }

  const selected = items.find((item) => item.id === selectedId);

  return (
    <div className="space-y-6">
      {error && (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800" role="alert">
          {error}
        </p>
      )}
      {items.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">
          No analyses yet. Run an analysis and it will show up here.
        </p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <div className="space-y-3">
            {items.map((item) => (
              <SummaryRow key={item.id} item={item} onSelect={() => setSelectedId(item.id)} />
            ))}
          </div>
          <div>
            {selected ? (
              <Results data={selected.payload || selected} />
            ) : (
              <p className="rounded-2xl border border-dashed border-slate-300 bg-ink-50/60 p-8 text-center text-sm text-slate-500">
                Select an entry to view its full analysis.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}