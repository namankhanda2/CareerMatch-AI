// Production: set VITE_API_BASE_URL at build time (e.g. the Render backend URL).
// Local dev: defaults to http://localhost:8000 so no env file is required.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
const TIMEOUT_MS = 60000;

async function postForm(url, form) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  let response;
  try {
    response = await fetch(`${API_BASE}${url}`, {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
  } catch {
    throw new Error("Could not reach the CareerMatch API. Please try again.");
  } finally {
    clearTimeout(timeout);
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : "Analysis failed. Please try again.");
  }
  return payload;
}

export async function analyzeResume(file, jobDescription) {
  const form = new FormData();
  form.append("resume", file);
  form.append("job_description", jobDescription);
  return postForm("/api/analyze", form);
}

export async function compareResume(file, jobDescriptions) {
  const form = new FormData();
  form.append("resume", file);
  form.append("job_descriptions", JSON.stringify(jobDescriptions));
  return postForm("/api/compare", form);
}

export async function fetchHistory(limit = 50) {
  let response;
  try {
    response = await fetch(`${API_BASE}/api/history?limit=${limit}`);
  } catch {
    throw new Error("Could not reach the CareerMatch API.");
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok || !payload) {
    throw new Error("Could not load analysis history.");
  }
  return payload.items ?? [];
}