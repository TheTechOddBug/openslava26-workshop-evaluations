import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api/client";
import { ModelSelect } from "../components/ModelControls";
import { MechanismPicker } from "../components/MechanismPicker";
import type { Catalog } from "../hooks/useCatalog";
import type { CandidateConfig, CellResult, EvalCase, EvalMethod, Run } from "../api/types";
import { DEFAULT_PARAMS } from "../api/types";
import { defaultJudgeId, isCandidate } from "../lib/catalog";
import { fmt, tone } from "../lib/format";

interface Candidate {
  model_id: string;
  prompt_override: string;
  label: string;
}

export function Matrix({ catalog }: { catalog: Catalog }) {
  const { models, evaluators, datasets } = catalog;
  const firstCandidate = models.find(isCandidate) ?? models[0];

  const [category, setCategory] = useState(datasets[0]?.category ?? "");
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [selectedCases, setSelectedCases] = useState<Set<string>>(new Set());
  const [candidates, setCandidates] = useState<Candidate[]>([
    { model_id: firstCandidate?.id ?? "", prompt_override: "", label: firstCandidate?.display_name ?? "A" },
  ]);
  const [methods, setMethods] = useState<Set<EvalMethod>>(new Set(["exact_match"]));
  const [judgeId, setJudgeId] = useState(defaultJudgeId(models));

  const [run, setRun] = useState<Run | null>(null);
  const [ranMethods, setRanMethods] = useState<EvalMethod[]>([]);
  const [thresholds, setThresholds] = useState<Partial<Record<EvalMethod, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const polling = useRef(false);

  const needsJudge = [...methods].some((m) => evaluators.find((e) => e.method === m)?.needs_judge);

  useEffect(() => {
    if (!category) return;
    api.listCases(category).then((cs) => {
      setCases(cs);
      setSelectedCases(new Set(cs.slice(0, 3).map((c) => c.id)));
    });
  }, [category]);

  useEffect(() => () => void (polling.current = false), []);

  const toggleCase = (id: string) =>
    setSelectedCases((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleMethod = (m: EvalMethod) =>
    setMethods((prev) => {
      const next = new Set(prev);
      next.has(m) ? next.delete(m) : next.add(m);
      return next;
    });

  const updateCandidate = (i: number, patch: Partial<Candidate>) =>
    setCandidates((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));

  const addCandidate = () =>
    setCandidates((prev) => [
      ...prev,
      { model_id: firstCandidate?.id ?? "", prompt_override: "", label: `Variant ${prev.length + 1}` },
    ]);

  const removeCandidate = (i: number) =>
    setCandidates((prev) => (prev.length > 1 ? prev.filter((_, idx) => idx !== i) : prev));

  const canRun = selectedCases.size > 0 && candidates.every((c) => c.model_id) && methods.size > 0;

  async function poll(runId: string) {
    if (!polling.current) return;
    try {
      const latest = await api.getRun(runId);
      setRun(latest);
      if (latest.status === "completed" || latest.status === "failed") {
        polling.current = false;
        return;
      }
    } catch {
      // transient; keep polling
    }
    setTimeout(() => poll(runId), 700);
  }

  async function start() {
    setError(null);
    setRun(null);
    try {
      const payloadCandidates: CandidateConfig[] = candidates.map((c) => ({
        model_id: c.model_id,
        params: DEFAULT_PARAMS,
        prompt_override: c.prompt_override.trim() || null,
        label: c.label.trim() || c.model_id,
      }));
      const created = await api.createRun({
        case_ids: [...selectedCases],
        candidates: payloadCandidates,
        methods: [...methods],
        judge_model_id: needsJudge ? judgeId : null,
      });
      setRun(created);
      setRanMethods([...methods]);
      polling.current = true;
      poll(created.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the run.");
    }
  }

  const columns = candidates.map((c) => c.label.trim() || c.model_id);

  return (
    <div className="split">
      <div>
        <div className="card">
          <div className="card__title">Cases</div>
          <label className="field">
            <span className="field__label">Category</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {datasets.map((d) => (
                <option key={d.category} value={d.category}>
                  {d.category} ({d.count})
                </option>
              ))}
            </select>
          </label>
          <div className="checklist" style={{ marginTop: 10, maxHeight: 200, overflow: "auto" }}>
            {cases.map((c) => (
              <label key={c.id} className={`check ${selectedCases.has(c.id) ? "check--on" : ""}`}>
                <input type="checkbox" checked={selectedCases.has(c.id)} onChange={() => toggleCase(c.id)} />
                <span className="check__label">{c.id}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card__title">Candidates</div>
          <div className="stack">
            {candidates.map((c, i) => (
              <div key={i} className="card" style={{ padding: 12 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <ModelSelect
                    label="Model"
                    models={models}
                    value={c.model_id}
                    onChange={(id) => updateCandidate(i, { model_id: id ?? "" })}
                    role="candidate"
                  />
                  {candidates.length > 1 && (
                    <button className="icon-button" title="Remove" onClick={() => removeCandidate(i)} style={{ marginTop: 20 }}>
                      ✕
                    </button>
                  )}
                </div>
                <label className="field" style={{ marginTop: 8 }}>
                  <span className="field__label">Label</span>
                  <input type="text" value={c.label} onChange={(e) => updateCandidate(i, { label: e.target.value })} />
                </label>
                <label className="field" style={{ marginTop: 8 }}>
                  <span className="field__label">Prompt override (optional)</span>
                  <textarea
                    value={c.prompt_override}
                    onChange={(e) => updateCandidate(i, { prompt_override: e.target.value })}
                    placeholder="Replace the case prompt — e.g. a refined version"
                    style={{ minHeight: 60 }}
                  />
                </label>
                <span className="field__hint">Write <code>{"{prompt}"}</code> where the case's own prompt should go.</span>
              </div>
            ))}
            <button className="btn" onClick={addCandidate}>
              Add candidate
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card__title">Mechanisms</div>
          <MechanismPicker evaluators={evaluators} selected={methods} onToggle={toggleMethod} applicable={null} />
          {needsJudge && (
            <div style={{ marginTop: 12 }}>
              <ModelSelect label="Judge model" models={models} value={judgeId} onChange={(id) => setJudgeId(id ?? "")} role="judge" />
            </div>
          )}
        </div>

        <button className="btn btn--primary" disabled={!canRun} onClick={start} style={{ width: "100%" }}>
          Run matrix
        </button>
      </div>

      <div>
        {error && <div className="banner">{error}</div>}
        {!run && !error && (
          <div className="empty">
            Pick cases and one or more candidates, then run. Give two candidates the same model
            but a naive and a refined prompt to see a smaller model catch up.
          </div>
        )}
        {run && (
          <div className="card">
            <div className="card__title">
              Results — {run.status} ({run.completed_cells}/{run.total_cells})
            </div>
            {run.status === "running" && (
              <div className="progress">
                <div
                  className="progress__fill"
                  style={{ width: `${run.total_cells ? (run.completed_cells / run.total_cells) * 100 : 0}%` }}
                />
              </div>
            )}
            <div className="gate-thresholds">
              <span className="field__label">Gate: block the release when a column's average is below</span>
              {ranMethods.map((m) => (
                <label key={m} className="gate-threshold">
                  <span>{m} ≥</span>
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={thresholds[m] ?? String(defaultThreshold(m))}
                    onChange={(e) => setThresholds((prev) => ({ ...prev, [m]: e.target.value }))}
                    aria-label={`${m} threshold`}
                  />
                </label>
              ))}
            </div>
            <div className="matrix" style={{ marginTop: 12 }}>
              <table>
                <thead>
                  <tr>
                    <th>Case</th>
                    {columns.map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...selectedCases].map((caseId) => (
                    <tr key={caseId}>
                      <td className="case">{caseId}</td>
                      {columns.map((col) => (
                        <td key={col}>
                          <CellView cell={run.results.find((r) => r.case_id === caseId && (r.label ?? r.model_id) === col)} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td className="case">Tokens</td>
                    {columns.map((col) => (
                      <td key={col}>
                        <UsageTotal cells={run.results.filter((r) => (r.label ?? r.model_id) === col && !r.error)} />
                      </td>
                    ))}
                  </tr>
                  <tr className="gate-row">
                    <td className="case">Gate</td>
                    {columns.map((col) => (
                      <td key={col}>
                        <GateCell
                          cells={run.results.filter((r) => (r.label ?? r.model_id) === col)}
                          methods={ranMethods}
                          threshold={(m) => thresholdValue(thresholds[m], m)}
                          done={run.status === "completed"}
                        />
                      </td>
                    ))}
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CellView({ cell }: { cell: CellResult | undefined }) {
  if (!cell) return <span className="muted">—</span>;
  if (cell.error) return <span className="chip chip--fail">error</span>;
  if (cell.scores.length === 0) return <span className="muted">n/a</span>;
  return (
    <div className="cell-scores">
      {cell.scores.map((s) => (
        <span key={s.method} className={`chip chip--${tone(s.value)}`}>
          {s.method}: {fmt(s.value)}
        </span>
      ))}
      <span className="cell-usage" title={`latency: ${cell.usage.latency_ms} ms`}>
        {tokens(cell.usage.prompt_tokens)} in · {tokens(cell.usage.completion_tokens)} out
      </span>
    </div>
  );
}

// Candidate tokens per column. Input tokens are where a longer, refined prompt shows its cost.
function UsageTotal({ cells }: { cells: CellResult[] }) {
  if (cells.length === 0) return <span className="muted">—</span>;
  const input = cells.reduce((sum, c) => sum + c.usage.prompt_tokens, 0);
  const output = cells.reduce((sum, c) => sum + c.usage.completion_tokens, 0);
  return (
    <span className="cell-usage cell-usage--total">
      {tokens(input)} in · {tokens(output)} out
    </span>
  );
}

const tokens = (n: number) => n.toLocaleString("en-US");

// The CI gate from Lab 07: a column passes when, for every mechanism, its average score
// over the cases reaches the threshold. A cell that errored counts as 0 for each
// mechanism; a mechanism that does not apply to a case is left out of that average.
const defaultThreshold = (m: EvalMethod) => (m === "llm_judge" ? 0.75 : 0.9);

function thresholdValue(raw: string | undefined, m: EvalMethod): number {
  const n = raw === undefined || raw.trim() === "" ? NaN : Number(raw);
  return Number.isFinite(n) ? n : defaultThreshold(m);
}

function GateCell({
  cells,
  methods,
  threshold,
  done,
}: {
  cells: CellResult[];
  methods: EvalMethod[];
  threshold: (m: EvalMethod) => number;
  done: boolean;
}) {
  if (!done) return <span className="muted">waiting for the run</span>;
  const checks = methods.flatMap((m) => {
    const values = cells.flatMap((c) => {
      if (c.error) return [0];
      const score = c.scores.find((s) => s.method === m);
      return score ? [score.value] : [];
    });
    if (values.length === 0) return [];
    const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
    return [{ method: m, mean, min: threshold(m), ok: mean >= threshold(m) }];
  });
  if (checks.length === 0) return <span className="muted">n/a</span>;
  const pass = checks.every((c) => c.ok);
  return (
    <div className="cell-scores">
      <span className={`gate-verdict gate-verdict--${pass ? "pass" : "blocked"}`}>{pass ? "PASS" : "BLOCKED"}</span>
      {checks.map((c) => (
        <span key={c.method} className="cell-usage" title={`needs ≥ ${fmt(c.min)}`}>
          {c.ok ? "✓" : "✗"} {c.method} {fmt(c.mean)} {c.ok ? "≥" : "<"} {fmt(c.min)}
        </span>
      ))}
    </div>
  );
}
