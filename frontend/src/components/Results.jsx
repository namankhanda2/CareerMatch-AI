import ScoreGauge from "./ScoreGauge.jsx";
import SkillPills from "./SkillPills.jsx";

function Section({ title, children }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      <h2 className="mb-4 text-lg font-semibold text-ink-900">{title}</h2>
      {children}
    </article>
  );
}

function dedupe(items) {
  return [...new Set((items || []).filter(Boolean))];
}

export default function Results({ data }) {
  const strengths = data.strengths || [];
  const gaps = data.gaps || [];
  const evidence = data.resume_evidence || {};
  const evidenceEntries = Object.entries(evidence);
  const ats = data.ats || {};
  const atsIssues = ats.issues || [];
  const matchingSkills = dedupe(data.matching_skills);
  const missingSkills = dedupe(data.missing_skills);

  return (
    <section className="space-y-6" aria-live="polite">
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <ScoreGauge score={data.match_score} label="match" />
          <div className="mt-4 flex items-center justify-between rounded-xl border border-slate-100 bg-ink-50/80 px-4 py-3">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Semantic similarity
            </span>
            <span className="text-sm font-semibold text-ink-800">
              {typeof data.semantic_score === "number" ? `${data.semantic_score}%` : "—"}
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between rounded-xl border border-slate-100 bg-ink-50/80 px-4 py-3">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              ATS readiness
            </span>
            <span className="text-sm font-semibold text-ink-800">
              {typeof ats.score === "number" ? `${ats.score}/100` : "—"}
            </span>
          </div>
        </article>

        <div className="grid gap-6 sm:grid-cols-2">
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Matching skills
            </h2>
            <SkillPills items={matchingSkills} variant="match" />
          </article>
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Missing skills
            </h2>
            <SkillPills items={missingSkills} variant="missing" />
          </article>
        </div>
      </div>

      {data.explanation && (
        <Section title="Why this score">
          <p className="text-sm leading-6 text-slate-700">{data.explanation}</p>
        </Section>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        {strengths.length > 0 && (
          <Section title="Strengths">
            <ul className="space-y-2">
              {strengths.map((item, index) => (
                <li
                  key={`${index}-${item}`}
                  className="flex gap-2 rounded-lg bg-emerald-50/70 px-3 py-2 text-sm text-emerald-800"
                >
                  <span aria-hidden="true">+</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}
        {gaps.length > 0 && (
          <Section title="Gaps">
            <ul className="space-y-2">
              {gaps.map((item, index) => (
                <li
                  key={`${index}-${item}`}
                  className="flex gap-2 rounded-lg bg-rose-50/70 px-3 py-2 text-sm text-rose-800"
                >
                  <span aria-hidden="true">−</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>

      {evidenceEntries.length > 0 && (
        <Section title="Evidence from your resume">
          <ul className="space-y-3">
            {evidenceEntries.map(([skill, quotes]) => (
              <li key={skill} className="rounded-xl border border-slate-100 bg-ink-50/60 p-4">
                <p className="text-sm font-semibold text-ink-800">{skill}</p>
                {(quotes || []).map((quote, i) => (
                  <p key={`${i}-${quote}`} className="mt-1 text-sm leading-6 text-slate-500">
                    “{quote}”
                  </p>
                ))}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {atsIssues.length > 0 && (
        <Section title="ATS checks">
          <ul className="space-y-2">
            {atsIssues.map((issue, index) => (
              <li
                key={`${index}-${issue}`}
                className="rounded-lg border border-amber-100 bg-amber-50/70 px-3 py-2 text-sm text-amber-800"
              >
                {issue}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {(data.suggestions || []).length > 0 && (
        <Section title="Improvement suggestions">
          <ol className="space-y-3">
            {data.suggestions.map((item, index) => (
              <li key={`${index}-${item}`} className="flex gap-3 text-sm leading-6 text-slate-700">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-600">
                  {index + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {(data.interview_questions || []).length > 0 && (
        <Section title="Likely interview questions">
          <ol className="space-y-4">
            {data.interview_questions.map((question, index) => (
              <li key={`${index}-${question}`} className="rounded-xl border border-slate-100 bg-ink-50/80 p-4">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-600">
                  Question {index + 1}
                </p>
                <p className="text-sm leading-6 text-slate-800">{question}</p>
              </li>
            ))}
          </ol>
        </Section>
      )}
    </section>
  );
}