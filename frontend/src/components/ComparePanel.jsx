import { useRef, useState } from "react";
import { compareResume } from "../api.js";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const SEPARATOR = "---";

function ScoreBar({ value }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0));
  const tone =
    clamped >= 70 ? "bg-emerald-500" : clamped >= 40 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}

function CompareCard({ result, index }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Option {index + 1}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-ink-900">{result.role || "Unparsed role"}</h3>
          {result.title_keywords?.length > 0 && (
            <p className="mt-1 text-sm text-slate-500">{result.title_keywords.join(" · ")}</p>
          )}
        </div>
        <p className="text-3xl font-semibold text-brand-600">{result.match_score}</p>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Fit</span>
          <ScoreBar value={result.match_score} />
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span className="pr-3">Semantic similarity {result.semantic_score}%</span>
          <ScoreBar value={result.semantic_score} />
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-emerald-700">
            Matched required
          </p>
          {(result.matched_required || []).length > 0 ? (
            <ul className="flex flex-wrap gap-1.5">
              {result.matched_required.map((skill) => (
                <li key={skill} className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
                  {skill}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">None.</p>
          )}
        </div>
        <div className="rounded-xl border border-rose-100 bg-rose-50/60 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-rose-700">
            Missing required
          </p>
          {(result.missing_required || []).length > 0 ? (
            <ul className="flex flex-wrap gap-1.5">
              {result.missing_required.map((skill) => (
                <li key={skill} className="rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-medium text-rose-800">
                  {skill}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">None.</p>
          )}
        </div>
      </div>

      {result.explanation && (
        <p className="mt-4 text-sm leading-6 text-slate-600">{result.explanation}</p>
      )}
    </article>
  );
}

export default function ComparePanel() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [jds, setJds] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState(null);

  function acceptFile(nextFile) {
    setError("");
    setResults(null);
    if (!nextFile) {
      setFile(null);
      return;
    }
    const isPdf =
      nextFile.type === "application/pdf" || nextFile.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setFile(null);
      setError("Please upload a PDF resume.");
      return;
    }
    if (nextFile.size > MAX_FILE_BYTES) {
      setFile(null);
      setError("Resume must be 5 MB or smaller.");
      return;
    }
    setFile(nextFile);
  }

  function parseJobDescriptions() {
    return jds
      .split(new RegExp(`^\\s*${SEPARATOR}\\s*$`, "m"))
      .map((part) => part.trim())
      .filter(Boolean);
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setResults(null);
    const list = parseJobDescriptions();
    if (!file) {
      setError("Upload a PDF resume to continue.");
      return;
    }
    if (list.length < 2) {
      setError(`Paste at least two job descriptions separated by a line with only "${SEPARATOR}".`);
      return;
    }

    setLoading(true);
    try {
      const data = await compareResume(file, list);
      setResults(
        [...data.results].sort((a, b) => b.match_score - a.match_score)
      );
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={onSubmit} className="grid gap-6 lg:grid-cols-2" noValidate>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
          <label htmlFor="compare-file" className="block text-sm font-semibold text-ink-900">
            Resume (PDF)
          </label>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-4 flex min-h-[180px] w-full flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-ink-50 px-4 py-8 text-center hover:border-brand-500 hover:bg-brand-50/40"
          >
            <span className="text-sm font-medium text-ink-800">
              {file ? file.name : "Click to choose a PDF"}
            </span>
            <span className="mt-1 text-xs text-slate-500">
              {file ? `${(file.size / 1024).toFixed(0)} KB` : "application/pdf"}
            </span>
          </button>
          <input
            id="compare-file"
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only"
            onChange={(event) => acceptFile(event.target.files?.[0])}
          />
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
          <label htmlFor="compare-jds" className="block text-sm font-semibold text-ink-900">
            Job descriptions to compare
          </label>
          <p className="mt-1 text-sm text-slate-500">
            Separate each job description with a line containing only “{SEPARATOR}”.
          </p>
          <textarea
            id="compare-jds"
            value={jds}
            onChange={(event) => {
              setJds(event.target.value);
              setResults(null);
            }}
            rows={12}
            placeholder={`Backend Engineer. Required: Python, FastAPI.\n${SEPARATOR}\nFrontend Developer. Required: React, TypeScript.`}
            className="mt-3 w-full resize-y rounded-xl border border-slate-200 bg-ink-50 px-3 py-3 text-sm leading-6 text-slate-800 outline-none ring-brand-500 placeholder:text-slate-400 focus:border-brand-500 focus:ring-2"
          />
        </div>

        <div className="lg:col-span-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800" role="alert">
              {error}
            </p>
          ) : (
            <p className="text-sm text-slate-500">
              Deterministic scoring only — no LLM calls, so results are instant.
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {loading ? "Comparing…" : "Compare roles"}
          </button>
        </div>
      </form>

      {results && (
        <div className="grid gap-6 lg:grid-cols-2">
          {results.map((result) => (
            <CompareCard key={result.index} result={result} index={result.index} />
          ))}
        </div>
      )}
    </div>
  );
}