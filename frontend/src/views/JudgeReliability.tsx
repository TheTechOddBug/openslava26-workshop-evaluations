import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api/client";
import { ModelSelect } from "../components/ModelControls";
import type { Catalog } from "../hooks/useCatalog";
import type { EvalCase, JudgeAgreement } from "../api/types";
import { DEFAULT_PARAMS, type Run } from "../api/types";
import { defaultCandidateId, defaultJudgeId, isJudge } from "../lib/catalog";
import { fmt } from "../lib/format";

type Phase = "idle" | "generating" | "comparing" | "done";

export function JudgeReliability({ catalog }: { catalog: Catalog }) {
  const { models, datasets } = catalog;

  const [category, setCategory] = useState(datasets[0]?.category ?? "");
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [candidateId, setCandidateId] = useState(defaultCandidateId(models));
  const judgeA = defaultJudgeId(models);
  const [judgeAId, setJudgeAId] = useState(judgeA);
  const [judgeBId, setJudgeBId] = useState(
    models.filter(isJudge).find((m) => m.id !== judgeA)?.id ?? judgeA,
  );

  const [phase, setPhase] = useState<Phase>("idle");
  const [agreement, setAgreement] = useState<JudgeAgreement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const polling = useRef(false);

  useEffect(() => {
    if (!category) return;
    api.listCases(category).then(setCases);
  }, [category]);

  useEffect(() => () => void (polling.current = false), []);

  const canRun = category && candidateId && judgeAId && judgeBId && cases.length > 0;

  function waitForRun(runId: string): Promise<Run> {
    return new Promise((resolve, reject) => {
      polling.current = true;
      const tick = async () => {
        if (!polling.current) return;
        try {
          const latest = await api.getRun(runId);
          if (latest.status === "completed") return resolve(latest);
          if (latest.status === "failed") return reject(new Error(latest.error ?? "run failed"));
        } catch {
          // transient
        }
        setTimeout(tick, 700);
      };
      tick();
    });
  }

  async function start() {
    setError(null);
    setAgreement(null);
    setPhase("generating");
    try {
      const created = await api.createRun({
        case_ids: cases.map((c) => c.id),
        candidates: [{ model_id: candidateId, params: DEFAULT_PARAMS }],
        methods: ["llm_judge"],
        judge_model_id: judgeAId,
      });
      await waitForRun(created.id);
      setPhase("comparing");
      const result = await api.judgeAgreement({
        run_id: created.id,
        reference_judge_model_id: judgeBId,
        sample_size: 25,
      });
      setAgreement(result);
      setPhase("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      setPhase("idle");
    }
  }

  return (
    <div className="split">
      <div>
        <div className="card">
          <div className="card__title">Setup</div>
          <div className="stack">
            <label className="field">
              <span className="field__label">Dataset category</span>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {datasets.map((d) => (
                  <option key={d.category} value={d.category}>
                    {d.category} ({d.count})
                  </option>
                ))}
              </select>
              <span className="field__hint">All {cases.length} cases are used.</span>
            </label>
            <ModelSelect label="Candidate model (writes the answers)" models={models} value={candidateId} onChange={(id) => setCandidateId(id ?? "")} role="candidate" />
            <ModelSelect label="Judge under test" models={models} value={judgeAId} onChange={(id) => setJudgeAId(id ?? "")} role="judge" />
            <ModelSelect label="Reference judge (assumed stronger)" models={models} value={judgeBId} onChange={(id) => setJudgeBId(id ?? "")} role="judge" />
          </div>
        </div>
        <button className="btn btn--primary" disabled={!canRun || phase === "generating" || phase === "comparing"} onClick={start} style={{ width: "100%" }}>
          {phase === "generating" ? "Generating answers…" : phase === "comparing" ? "Comparing judges…" : "Measure agreement"}
        </button>
      </div>

      <div>
        {error && <div className="banner">{error}</div>}
        {!agreement && !error && (
          <div className="empty">
            This measures whether a judge can be trusted: the candidate answers every case, the
            judge under test scores them, then a reference judge re-scores a sample. Low agreement
            means the judge is unreliable for this task.
          </div>
        )}
        {agreement && (
          <>
            <div className="card">
              <div className="card__title">Verdict — sample of {agreement.sample_size}</div>
              <span className={`verdict verdict--${agreement.verdict}`}>{agreement.verdict}</span>
            </div>
            <div className="card">
              <div className="card__title">Agreement metrics</div>
              <div className="metric-grid">
                <Metric label="Pearson r" value={fmt(agreement.pearson)} />
                <Metric label="Spearman ρ" value={fmt(agreement.spearman)} />
                <Metric label="Rank agreement" value={fmt(agreement.rank_agreement)} />
                <Metric label="Mean abs. error" value={fmt(agreement.mae_overall)} />
              </div>
            </div>
            <div className="card">
              <div className="card__title">Error by dimension (0–10 scale)</div>
              <div className="dims">
                {Object.entries(agreement.mae_by_dimension).map(([dim, value]) => (
                  <DimError key={dim} name={dim} value={value} />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <div className="metric__value">{value}</div>
      <div className="metric__label">{label}</div>
    </div>
  );
}

function DimError({ name, value }: { name: string; value: number }) {
  return (
    <>
      <span className="dims__name">{name}</span>
      <div className="scorebar">
        <div
          className="scorebar__fill"
          style={{ width: `${Math.min(1, value / 5) * 100}%`, background: value <= 1.5 ? "var(--pass)" : "var(--fail)" }}
        />
      </div>
      <span className="dims__value">{value.toFixed(2)}</span>
    </>
  );
}
