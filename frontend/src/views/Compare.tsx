import { useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import { ModelSelect } from "../components/ModelControls";
import type { Catalog } from "../hooks/useCatalog";
import type { EvalCase, PairwiseResult, PairwiseVerdict } from "../api/types";
import { defaultCandidateId, defaultJudgeId, isCandidate } from "../lib/catalog";

const VERDICT_LABEL: Record<PairwiseVerdict, string> = {
  a: "Model A wins",
  b: "Model B wins",
  tie: "Tie",
};

export function Compare({ catalog }: { catalog: Catalog }) {
  const { models, datasets } = catalog;
  const secondCandidate = models.filter(isCandidate)[1]?.id ?? defaultCandidateId(models);

  const [category, setCategory] = useState(datasets[0]?.category ?? "");
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [caseId, setCaseId] = useState("");
  const [modelA, setModelA] = useState(defaultCandidateId(models));
  const [modelB, setModelB] = useState(secondCandidate);
  const [overrideA, setOverrideA] = useState("");
  const [overrideB, setOverrideB] = useState("");
  const [judgeId, setJudgeId] = useState(defaultJudgeId(models));
  const [swap, setSwap] = useState(true);

  const [result, setResult] = useState<PairwiseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!category) return;
    api.listCases(category).then((cs) => {
      setCases(cs);
      setCaseId(cs[0]?.id ?? "");
    });
  }, [category]);

  const canRun = caseId && modelA && modelB && judgeId;

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.compare({
        case_id: caseId,
        model_a: modelA,
        model_b: modelB,
        judge_model_id: judgeId,
        prompt_override_a: overrideA.trim() || null,
        prompt_override_b: overrideB.trim() || null,
        swap,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Comparison failed.");
    } finally {
      setLoading(false);
    }
  }

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
          <div className="card__title">Candidate A</div>
          <ModelSelect label="Model A" models={models} value={modelA} onChange={(id) => setModelA(id ?? "")} role="candidate" />
          <label className="field" style={{ marginTop: 8 }}>
            <span className="field__label">Prompt override (optional)</span>
            <textarea value={overrideA} onChange={(e) => setOverrideA(e.target.value)} style={{ minHeight: 56 }} />
          </label>
          <span className="field__hint">Write <code>{"{prompt}"}</code> where the case's own prompt should go.</span>
        </div>

        <div className="card">
          <div className="card__title">Candidate B</div>
          <ModelSelect label="Model B" models={models} value={modelB} onChange={(id) => setModelB(id ?? "")} role="candidate" />
          <label className="field" style={{ marginTop: 8 }}>
            <span className="field__label">Prompt override (optional)</span>
            <textarea value={overrideB} onChange={(e) => setOverrideB(e.target.value)} style={{ minHeight: 56 }} />
          </label>
          <span className="field__hint">Write <code>{"{prompt}"}</code> where the case's own prompt should go.</span>
        </div>

        <div className="card">
          <div className="card__title">Judge</div>
          <ModelSelect label="Judge model" models={models} value={judgeId} onChange={(id) => setJudgeId(id ?? "")} role="judge" />
          <label className="check" style={{ marginTop: 8 }}>
            <input type="checkbox" checked={swap} onChange={(e) => setSwap(e.target.checked)} />
            <span>
              <span className="check__label">Swap positions to check for bias</span>
              <span className="check__desc">Re-judge with A and B swapped; a flipped winner reveals position bias.</span>
            </span>
          </label>
        </div>

        <button className="btn btn--primary" disabled={!canRun || loading} onClick={run} style={{ width: "100%" }}>
          {loading ? "Comparing…" : "Compare"}
        </button>
      </div>

      <div>
        {error && <div className="banner">{error}</div>}
        {!result && !error && (
          <div className="empty">
            Pick a case and two candidate models. The judge decides which answer is better; swap
            the positions to see whether its verdict depends on the answer or just the order.
          </div>
        )}
        {result?.error && <div className="banner">{result.error}</div>}
        {result && !result.error && (
          <>
            <div className="card">
              <div className="card__title">Verdict — judged by {result.judge_model}</div>
              <span className={`verdict ${result.verdict === "tie" ? "verdict--questionable" : "verdict--reliable"}`}>
                {VERDICT_LABEL[result.verdict]}
              </span>
              {result.position_bias === true && (
                <div className="banner" style={{ marginTop: 12 }}>
                  Position bias: the winner changed when the answers were swapped (swapped verdict:{" "}
                  {VERDICT_LABEL[result.swapped_verdict ?? "tie"]}). This judge is influenced by
                  order, not just quality.
                </div>
              )}
              {result.position_bias === false && (
                <p className="muted" style={{ marginTop: 12 }}>
                  Consistent under swap — no position bias detected.
                </p>
              )}
              {result.justification && <div className="score-card__detail">{result.justification}</div>}
            </div>
            <div className="card">
              <div className="card__title">Answer A — {result.model_a}</div>
              <div className="response">{result.response_a || "(empty)"}</div>
            </div>
            <div className="card">
              <div className="card__title">Answer B — {result.model_b}</div>
              <div className="response">{result.response_b || "(empty)"}</div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
