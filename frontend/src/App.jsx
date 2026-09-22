import { useId, useRef, useState } from "react";
import { analyzeResume } from "./api.js";
import ComparePanel from "./components/ComparePanel.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";
import Results from "./components/Results.jsx";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

const TABS = [
  { id: "analyze", label: "Analyze" },
  { id: "compare", label: "Compare roles" },
  { id: "history", label: "History" },
];

export default function App() {
  const fileInputId = useId();
  const inputRef = useRef(null);
  const [tab, setTab] = useState("analyze");
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  function acceptFile(nextFile) {
    setError("");
    setResult(null);
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

  function clearFile() {
    setFile(null);
    setError("");
    setResult(null);
  }

  function handleJobDescriptionChange(value) {
    setJobDescription(value);
    setResult(null);
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!file) {
      setError("Upload a PDF resume to continue.");
      return;
    }
    if (!jobDescription.trim()) {
      setError("Paste a job description to continue.");
      return;
    }

    setLoading(true);
    try {
      const data = await analyzeResume(file, jobDescription.trim());
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/80 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-5 sm:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">
              CareerMatch AI
            </p>
            <h1 className="mt-1 text-xl font-semibold text-ink-900 sm:text-2xl">
              Resume-to-role matching
            </h1>
          </div>
          <p className="hidden max-w-xs text-right text-sm text-slate-500 sm:block">
            Upload a resume, paste a job description, and get a clear fit analysis.
          </p>
        </div>
      </header>

      <nav className="border-b border-slate-200/80 bg-white">
        <div className="mx-auto flex max-w-5xl gap-1 px-4 pb-0 pt-1 sm:px-6">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`rounded-t-lg px-4 py-2.5 text-sm font-medium transition ${
                tab === item.id
                  ? "bg-ink-50 text-brand-600 shadow-sm"
                  : "text-slate-500 hover:text-ink-800"
              }`}
              aria-current={tab === item.id ? "page" : undefined}
            >
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="mx-auto max-w-5xl space-y-8 px-4 py-8 sm:px-6 sm:py-10">
        {tab === "history" && <HistoryPanel />}
        {tab === "compare" && <ComparePanel />}
        {tab === "analyze" && (
          <>
            <form
              onSubmit={onSubmit}
              className="grid gap-6 lg:grid-cols-2"
              noValidate
            >
          <div
            className={`rounded-2xl border bg-white p-5 shadow-card transition ${
              dragOver ? "border-brand-500 ring-2 ring-brand-50" : "border-slate-200"
            }`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              acceptFile(event.dataTransfer.files?.[0]);
            }}
          >
            <label htmlFor={fileInputId} className="block text-sm font-semibold text-ink-900">
              Resume (PDF)
            </label>
            <p className="mt-1 text-sm text-slate-500">Max 5 MB. Text-based PDFs work best.</p>
            <button
              type="button"
              className="mt-4 flex min-h-[220px] w-full flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-ink-50 px-4 py-10 text-center hover:border-brand-500 hover:bg-brand-50/40"
              onClick={() => inputRef.current?.click()}
            >
              <span className="text-sm font-medium text-ink-800">
                {file ? file.name : "Drop a PDF here or click to browse"}
              </span>
              <span className="mt-1 text-xs text-slate-500">
                {file ? `${(file.size / 1024).toFixed(0)} KB` : "application/pdf"}
              </span>
              {file && (
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(event) => {
                    event.stopPropagation();
                    clearFile();
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      clearFile();
                    }
                  }}
                  className="mt-3 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-rose-200 hover:text-rose-700"
                >
                  Remove file
                </span>
              )}
            </button>
            <input
              id={fileInputId}
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={(event) => acceptFile(event.target.files?.[0])}
            />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <label htmlFor="job-description" className="block text-sm font-semibold text-ink-900">
              Job description
            </label>
            <p className="mt-1 text-sm text-slate-500">
              Paste the full posting, including required skills.
            </p>
            <textarea
              id="job-description"
              value={jobDescription}
              onChange={(event) => handleJobDescriptionChange(event.target.value)}
              rows={10}
              maxLength={12000}
              placeholder="Paste the job description here…"
              className="mt-4 w-full resize-y rounded-xl border border-slate-200 bg-ink-50 px-3 py-3 text-sm leading-6 text-slate-800 outline-none ring-brand-500 placeholder:text-slate-400 focus:border-brand-500 focus:ring-2"
            />
            <p className="mt-2 text-right text-xs text-slate-400">
              {jobDescription.length.toLocaleString()} / 12,000
            </p>
          </div>

          <div className="lg:col-span-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {error ? (
              <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800" role="alert">
                {error}
              </p>
            ) : (
              <p className="text-sm text-slate-500">
                Analyses are saved to your local history in the History tab.
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {loading ? "Analyzing…" : "Analyze match"}
            </button>
          </div>
        </form>

        {loading && (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-card">
            <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-brand-600" />
            <p className="text-sm font-medium text-ink-800">Reading the resume and scoring fit…</p>
            <p className="mt-1 text-sm text-slate-500">This usually takes a few seconds.</p>
          </div>
        )}

        {result && !loading && <Results data={result} />}
          </>
        )}
      </main>
    </div>
  );
}
