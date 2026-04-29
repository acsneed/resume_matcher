import io
import json
import os
import re
from typing import Dict, List

from flask import Flask, render_template_string, request
import google.generativeai as genai
from PyPDF2 import PdfReader
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Resume Intelligence Studio</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel-light: #1f2937;
      --ink: #e5e7eb;
      --muted: #9ca3af;
      --accent: #22d3ee;
      --accent-2: #a78bfa;
      --good: #10b981;
      --warn: #f59e0b;
      --danger: #ef4444;
      --line: #334155;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, Arial, sans-serif;
      background:
        radial-gradient(1100px 450px at 20% -10%, rgba(34, 211, 238, 0.16), transparent 55%),
        radial-gradient(900px 400px at 90% 0%, rgba(167, 139, 250, 0.14), transparent 48%),
        var(--bg);
      color: var(--ink);
      line-height: 1.4;
    }

    .container { max-width: 1100px; margin: 2.2rem auto 3rem; padding: 0 1rem; }
    .panel {
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.01));
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 1.1rem 1.1rem;
      box-shadow: 0 20px 30px rgba(0, 0, 0, 0.22);
      margin-bottom: 1rem;
    }
    .hero h1 { margin: 0.2rem 0 0.3rem; font-size: 1.8rem; }
    .muted { color: var(--muted); font-size: 0.95rem; }
    .kicker {
      display: inline-block;
      font-size: 0.77rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #c4b5fd;
      margin-bottom: 0.2rem;
    }

    .form-grid { display: grid; grid-template-columns: 1fr; gap: 0.8rem; }
    label { display: block; font-weight: 600; margin-bottom: 0.4rem; }
    input[type=file], textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      color: var(--ink);
      padding: 0.7rem;
    }
    textarea { min-height: 220px; resize: vertical; }
    button {
      margin-top: 0.2rem;
      border: 0;
      border-radius: 10px;
      padding: 0.65rem 1rem;
      color: #0f172a;
      font-weight: 700;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      cursor: pointer;
    }
    .error {
      border: 1px solid rgba(239, 68, 68, 0.45);
      background: rgba(127, 29, 29, 0.25);
      color: #fecaca;
      border-radius: 10px;
      padding: 0.8rem;
      margin-bottom: 1rem;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 0.7rem;
      margin: 0.5rem 0 0.1rem;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      padding: 0.75rem;
    }
    .metric .name { color: var(--muted); font-size: 0.8rem; }
    .metric .val { font-size: 1.25rem; font-weight: 700; margin-top: 0.15rem; }

    .grid-3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(180px, 1fr));
      gap: 0.8rem;
      margin-top: 0.7rem;
    }
    .col-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      padding: 0.75rem;
    }
    .col-card h3 { margin: 0; font-size: 0.95rem; }
    ul.clean {
      list-style: none;
      margin: 0.55rem 0 0;
      padding: 0;
      display: grid;
      gap: 0.4rem;
    }
    ul.clean li {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0.35rem 0.6rem;
      background: var(--panel-light);
      font-size: 0.88rem;
    }

    table { width: 100%; border-collapse: collapse; margin-top: 1rem; border-radius: 10px; overflow: hidden; }
    th, td { border: 1px solid var(--line); padding: 0.58rem; vertical-align: top; font-size: 0.9rem; }
    th { background: rgba(148, 163, 184, 0.1); text-align: left; }

    details {
      margin-top: 0.8rem;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      padding: 0.5rem 0.75rem;
    }
    pre {
      white-space: pre-wrap;
      color: #d1d5db;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.78rem;
      max-height: 250px;
      overflow: auto;
    }
    .footer-note { margin-top: 0.6rem; color: var(--muted); font-size: 0.82rem; }
    @media (max-width: 860px) {
      .metrics { grid-template-columns: repeat(2, minmax(100px, 1fr)); }
      .grid-3 { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="panel hero">
      <span class="kicker">Ethical Recruiting AI</span>
      <h1>Resume Intelligence Studio</h1>
      <p class="muted">
        Upload a PDF resume and paste a job description to detect skill, keyword, and qualification gaps.
        This app anonymizes resume content before analysis and does not provide match scores.
      </p>
    </div>

    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}

    <div class="panel">
      <form method="post" enctype="multipart/form-data">
        <div class="form-grid">
          <div>
            <label>Resume PDF</label>
            <input type="file" name="resume_pdf" accept=".pdf" required>
          </div>

          <div>
            <label>Job Description</label>
            <textarea name="job_description" placeholder="Paste the full job description here..." required>{{ job_description }}</textarea>
          </div>
        </div>

        <button type="submit">Run Analysis</button>
      </form>
    </div>

    {% if results %}
      <div class="panel">
        <h2>Analysis Results</h2>
        <p class="muted">Structured output with strengths, gaps, and next-step optimization tips.</p>

        <div class="metrics">
          <div class="metric"><div class="name">Matched Skills</div><div class="val">{{ metrics.matched }}</div></div>
          <div class="metric"><div class="name">Missing Skills</div><div class="val">{{ metrics.missing_skills }}</div></div>
          <div class="metric"><div class="name">Missing Keywords</div><div class="val">{{ metrics.missing_keywords }}</div></div>
          <div class="metric"><div class="name">Missing Qualifications</div><div class="val">{{ metrics.missing_qualifications }}</div></div>
        </div>

        <div class="grid-3">
          <div class="col-card">
            <h3>Matched Skills</h3>
            <ul class="clean">
              {% for item in results.matched_skills %}
                <li>{{ item }}</li>
              {% else %}
                <li>No direct matches identified.</li>
              {% endfor %}
            </ul>
          </div>
          <div class="col-card">
            <h3>Missing Skills</h3>
            <ul class="clean">
              {% for item in results.missing_skills %}
                <li>{{ item }}</li>
              {% else %}
                <li>No major missing skills found.</li>
              {% endfor %}
            </ul>
          </div>
          <div class="col-card">
            <h3>Optimization Tips</h3>
            <ul class="clean">
              {% for item in results.optimization_tips %}
                <li>{{ item }}</li>
              {% else %}
                <li>No optimization tips provided.</li>
              {% endfor %}
            </ul>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Missing Skills</th>
              <th>Missing Keywords</th>
              <th>Missing Qualifications</th>
            </tr>
          </thead>
          <tbody>
            {% for row in table_rows %}
            <tr>
              <td>{{ row[0] }}</td>
              <td>{{ row[1] }}</td>
              <td>{{ row[2] }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>

      </div>
    {% endif %}
  </div>
</body>
</html>
"""


def extract_resume_text_from_pdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: List[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def scrub_resume_pii(resume_text: str) -> str:
    if not resume_text:
        return ""

    scrubbed = resume_text
    scrubbed = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", scrubbed)
    scrubbed = re.sub(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b", "[REDACTED_PHONE]", scrubbed)

    lines = scrubbed.splitlines()
    for i, line in enumerate(lines):
        candidate = line.strip()
        if candidate and re.fullmatch(r"[A-Za-z][A-Za-z\s\-.']{1,50}", candidate):
            if 2 <= len(candidate.split()) <= 4:
                lines[i] = "[REDACTED_NAME]"
            break
    return "\n".join(lines)


def analyze_with_gemini(anonymized_resume_text: str, job_description: str) -> Dict[str, List[str]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)
    prompt = f"""
Compare the resume and job description.
Return only valid JSON with this schema:
{{
  "matched_skills": ["..."],
  "missing_skills": ["..."],
  "missing_keywords": ["..."],
  "missing_qualifications": ["..."],
  "optimization_tips": ["..."]
}}

Rules:
- Be concise and specific.
- Include only gaps that are important for the role.
- Do not include scores or rankings.
- Add practical optimization tips for improving resume-job alignment.

Resume (anonymized):
{anonymized_resume_text}

Job Description:
{job_description}
""".strip()

    available_generate_models: List[str] = []
    for m in genai.list_models():
        methods = getattr(m, "supported_generation_methods", []) or []
        if "generateContent" in methods:
            # API often returns names as "models/<id>"; sdk expects "<id>".
            available_generate_models.append(m.name.replace("models/", ""))

    preferred_models = [
        "gemini-3-flash-preview",    # Current latest Flash
        "gemini-3.1-flash-lite-preview", # Highest daily limit
        "gemini-2.5-flash",          # Reliable backup
        "gemini-1.5-flash",          # Stable legacy
    ]
    model_names = [name for name in preferred_models if name in available_generate_models]
    if not model_names:
        model_names = available_generate_models

    if not model_names:
        raise ValueError("No Gemini models with generateContent support are available for this key.")

    response = None
    last_error: Exception | None = None
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                [
                    "You extract candidate job-fit gaps from text.",
                    prompt,
                ],
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            break
        except Exception as exc:  # pragma: no cover - network/API variability
            last_error = exc

    if response is None:
        raise ValueError(f"No supported Gemini model available. Last error: {last_error}")
    payload = json.loads(response.text or "{}")
    return {
        "matched_skills": payload.get("matched_skills", []),
        "missing_skills": payload.get("missing_skills", []),
        "missing_keywords": payload.get("missing_keywords", []),
        "missing_qualifications": payload.get("missing_qualifications", []),
        "optimization_tips": payload.get("optimization_tips", []),
    }


def build_rows(results: Dict[str, List[str]]) -> List[List[str]]:
    skills = results.get("missing_skills", [])
    keywords = results.get("missing_keywords", [])
    quals = results.get("missing_qualifications", [])
    max_len = max(len(skills), len(keywords), len(quals), 1)

    rows: List[List[str]] = []
    for i in range(max_len):
        rows.append([
            skills[i] if i < len(skills) else "",
            keywords[i] if i < len(keywords) else "",
            quals[i] if i < len(quals) else "",
        ])
    return rows


def build_metrics(results: Dict[str, List[str]]) -> Dict[str, int]:
    return {
        "matched": len(results.get("matched_skills", [])),
        "missing_skills": len(results.get("missing_skills", [])),
        "missing_keywords": len(results.get("missing_keywords", [])),
        "missing_qualifications": len(results.get("missing_qualifications", [])),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    error = ""
    results = None
    rows: List[List[str]] = []
    metrics = {"matched": 0, "missing_skills": 0, "missing_keywords": 0, "missing_qualifications": 0}
    job_description = ""
    anonymized_preview = ""

    if request.method == "POST":
        pdf_file = request.files.get("resume_pdf")
        job_description = request.form.get("job_description", "").strip()

        if not pdf_file or not pdf_file.filename.lower().endswith(".pdf"):
            error = "Please upload a valid PDF resume."
        elif not job_description:
            error = "Please paste a job description."
        else:
            try:
                resume_text = extract_resume_text_from_pdf(pdf_file.read())
                if not resume_text:
                    raise ValueError("Could not extract text from this PDF.")
                anonymized = scrub_resume_pii(resume_text)
                anonymized_preview = anonymized[:5000]
                results = analyze_with_gemini(anonymized, job_description)
                rows = build_rows(results)
                metrics = build_metrics(results)
            except Exception as exc:
                error = f"Analysis failed: {exc}"

    return render_template_string(
        HTML_TEMPLATE,
        error=error,
        results=results,
        table_rows=rows,
        metrics=metrics,
        job_description=job_description,
        anonymized_preview=anonymized_preview,
    )


if __name__ == "__main__":
    app.run(debug=True)
