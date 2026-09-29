import { useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import { ModelSelect } from "../components/ModelControls";
import type { Catalog } from "../hooks/useCatalog";
import type { EnsembleResult, EvalCase } from "../api/types";
import { defaultCandidateId, isJudge } from "../lib/catalog";
import { JUDGE_DIMENSIONS, fmt } from "../lib/format";

export function Ensemble({ catalog }: { catalog: Catalog }) {
  const { models, datasets } = catalog;
  const judges = models.filter(isJudge);

  const [category, setCategory] = useState(datasets[0]?.category ?? "");
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [caseId, setCaseId] = useState("");
  const [modelId, setModelId] = useState(defaultCandidateId(models));
  const [judgeIds, setJudgeIds] = useState<Set<string>>(
    new Set(judges.slice(0, 3).map((j) => j.id)),
  );

  const [result, setResult] = useState<EnsembleResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!category) return;
    api.listCases(category).then((cs) => {
      setCases(cs);
      setCaseId(cs[0]?.id ?? "");
    });
  }, [category]);

  const toggleJudge = (id: string) =>
    setJudgeIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const canRun = caseId && modelId && judgeIds.size > 0;

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.ensembleJudge({
        case_id: caseId,
        model_id: modelId,
        judge_model_ids: [...judgeIds],
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ensemble judging failed.");
    } finally {
      setLoading(false);
    }
  }

  const nameOf = (id: string) => models.find((m) => m.id === id)?.display_name ?? id;

  return (
    <div className="split">
      <div>
        <div className="card">
          <div className="card__title">Case</div>
          <div className="stack">
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
            <label className="field">
              <span className="field__label">Case</span>
              <select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="card">
          <div className="card__title">Candidate</div>
          <ModelSelect label="Model" models={models} value={modelId} onChange={(id) => setModelId(id ?? "")} role="candidate" />
        </div>

        <div className="card">
          <div className="card__title">Panel of judges</div>
          <div className="checklist">
            {judges.map((j) => (
              <label key={j.id} className={`check ${judgeIds.has(j.id) ? "check--on" : ""}`}>
                <input type="checkbox" checked={judgeIds.has(j.id)} onChange={() => toggleJudge(j.id)} />
                <span className="check__label">{j.display_name}</span>
              </label>
            ))}
          </div>
        </div>

        <button className="btn btn--primary" disabled={!canRun || loading} onClick={run} style={{ width: "100%" }}>
          {loading ? "Judging…" : "Run ensemble"}
        </button>
      </div>

      <div>
        {error && <div className="banner">{error}</div>}
        {!result && !error && (
          <div className="empty">
            One answer, several judges. Averaging independent judges smooths out any single
            model's quirks; a wide spread means the judges disagree and the average is shakier.
          </div>
        )}
        {result?.error && <div className="banner">{result.error}</div>}
        {result && !result.error && (
          <>
            <div className="card">
              <div className="card__title">Ensemble score — {result.per_judge.length} judges</div>
              <div className="metric-grid">
                <div className="metric">
                  <div className="metric__value">{fmt(result.ensemble_score)}</div>
                  <div className="metric__label">Average score</div>
                </div>
                <div className="metric">
                  <div className="metric__value">{fmt(result.spread)}</div>
                  <div className="metric__label">Spread (disagreement)</div>
                </div>
              </div>
              <div className="dims" style={{ marginTop: 12 }}>
                {JUDGE_DIMENSIONS.filter((d) => result.ensemble_dimensions[d] !== undefined).map((d) => (
                  <DimBar key={d} name={d} value={result.ensemble_dimensions[d]} />
                ))}
              </div>
            </div>
            <div className="card">
              <div className="card__title">Per judge</div>
              <div className="dims">
                {result.per_judge.map((j) => (
                  <ScoreRow key={j.judge_model} name={nameOf(j.judge_model)} value={j.score} />
                ))}
              </div>
            </div>
            <div className="card">
              <div className="card__title">Answer</div>
              <div className="response">{result.response || "(empty)"}</div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function DimBar({ name, value }: { name: string; value: number }) {
  return (
    <>
      <span className="dims__name">{name}</span>
      <div className="scorebar">
        <div className="scorebar__fill" style={{ width: `${(value / 10) * 100}%`, background: "var(--accent)" }} />
      </div>
      <span className="dims__value">{value.toFixed(1)}</span>
    </>
  );
}

function ScoreRow({ name, value }: { name: string; value: number }) {
  return (
    <>
      <span className="dims__name">{name}</span>
      <div className="scorebar">
        <div className="scorebar__fill" style={{ width: `${value * 100}%`, background: "var(--accent)" }} />
      </div>
      <span className="dims__value">{value.toFixed(2)}</span>
    </>
  );
}
