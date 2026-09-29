import { useEffect, useMemo, useState } from "react";

import { ApiError, api } from "../api/client";
import { ModelSelect, ParamControls } from "../components/ModelControls";
import { MechanismPicker } from "../components/MechanismPicker";
import { ScoreCard } from "../components/ScoreCard";
import type { Catalog } from "../hooks/useCatalog";
import type { CellResult, EvalCase, EvalMethod, EvaluatorInfo, RunParams } from "../api/types";
import { DEFAULT_PARAMS } from "../api/types";
import { defaultCandidateId, defaultJudgeId } from "../lib/catalog";

type Source = "dataset" | "custom";

function applicableForFields(evaluators: EvaluatorInfo[], present: Set<string>): Set<string> {
  const set = new Set<string>();
  for (const ev of evaluators) {
    if (ev.required_fields.every((f) => present.has(f))) set.add(ev.method);
  }
  return set;
}

export function Playground({ catalog }: { catalog: Catalog }) {
  const { models, evaluators, datasets } = catalog;
  const labelFor = useMemo(
    () => new Map(evaluators.map((e) => [e.method, e.label] as const)),
    [evaluators],
  );

  const [source, setSource] = useState<Source>("dataset");
  const [category, setCategory] = useState(datasets[0]?.category ?? "");
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [caseId, setCaseId] = useState<string>("");
  const [applicable, setApplicable] = useState<Set<string> | null>(null);

  const [customPrompt, setCustomPrompt] = useState("");
  const [customReference, setCustomReference] = useState("");
  const [customRubric, setCustomRubric] = useState("");

  const [modelId, setModelId] = useState(defaultCandidateId(models));
  const [params, setParams] = useState<RunParams>({ ...DEFAULT_PARAMS });
  const [methods, setMethods] = useState<Set<EvalMethod>>(new Set());
  const [judgeId, setJudgeId] = useState(defaultJudgeId(models));

  const [result, setResult] = useState<CellResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCase = cases.find((c) => c.id === caseId) ?? null;
  const candidate = models.find((m) => m.id === modelId) ?? null;
  const needsJudge = [...methods].some((m) => evaluators.find((e) => e.method === m)?.needs_judge);

  // Load cases when the category changes.
  useEffect(() => {
    if (source !== "dataset" || !category) return;
    api.listCases(category).then((cs) => {
      setCases(cs);
      setCaseId(cs[0]?.id ?? "");
    });
  }, [source, category]);

  // Refresh applicable mechanisms for the chosen case (from the backend).
  useEffect(() => {
    if (source !== "dataset" || !caseId) return;
    api.applicableMethods(caseId).then((ms) => {
      const set = new Set(ms);
      setApplicable(set);
      setMethods((prev) => new Set([...prev].filter((m) => set.has(m))));
    });
  }, [source, caseId]);

  // In custom mode, applicability is derived from the fields the user filled in.
  useEffect(() => {
    if (source !== "custom") return;
    const present = new Set<string>();
    if (customReference.trim()) present.add("reference");
    if (customRubric.trim()) present.add("rubric");
    const set = applicableForFields(evaluators, present);
    setApplicable(set);
    setMethods((prev) => new Set([...prev].filter((m) => set.has(m))));
  }, [source, customReference, customRubric, evaluators]);

  const toggle = (m: EvalMethod) =>
    setMethods((prev) => {
      const next = new Set(prev);
      next.has(m) ? next.delete(m) : next.add(m);
      return next;
    });

  const canRun =
    modelId &&
    methods.size > 0 &&
    (source === "dataset" ? !!caseId : customPrompt.trim().length > 0) &&
    (!needsJudge || !!judgeId);

  async function evaluate() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const rubric = customRubric
        .split("\n")
        .map((r) => r.trim())
        .filter(Boolean);
      const body =
        source === "dataset"
          ? { case_id: caseId }
          : {
              prompt: customPrompt,
              reference: customReference.trim() || null,
              rubric: rubric.length ? rubric : null,
            };
      const res = await api.evaluate({
        model_id: modelId,
        methods: [...methods],
        params,
        judge_model_id: needsJudge ? judgeId : null,
        ...body,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Evaluation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="split">
      <div>
        <div className="card">
          <div className="card__title">Prompt</div>
          <div className="row" style={{ marginBottom: 12 }}>
            <button
              className={`tab ${source === "dataset" ? "tab--active" : ""}`}
              onClick={() => setSource("dataset")}
            >
              From dataset
            </button>
            <button
              className={`tab ${source === "custom" ? "tab--active" : ""}`}
              onClick={() => setSource("custom")}
            >
              Custom
            </button>
          </div>

          {source === "dataset" ? (
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
              {selectedCase && (
                <div className="response" style={{ maxHeight: 160 }}>
                  {selectedCase.prompt}
                </div>
              )}
            </div>
          ) : (
            <div className="stack">
              <label className="field">
                <span className="field__label">Prompt</span>
                <textarea value={customPrompt} onChange={(e) => setCustomPrompt(e.target.value)} />
              </label>
              <label className="field">
                <span className="field__label">Reference answer (optional)</span>
                <input
                  type="text"
                  value={customReference}
                  onChange={(e) => setCustomReference(e.target.value)}
                  placeholder="enables exact match and similarity"
                />
              </label>
              <label className="field">
                <span className="field__label">Judge rubric, one per line (optional)</span>
                <textarea
                  value={customRubric}
                  onChange={(e) => setCustomRubric(e.target.value)}
                  style={{ minHeight: 64 }}
                />
              </label>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card__title">Model</div>
          <div className="stack">
            <ModelSelect
              label="Candidate model"
              models={models}
              value={modelId}
              onChange={(id) => setModelId(id ?? "")}
              role="candidate"
            />
            <ParamControls
              params={params}
              onChange={setParams}
              supportsReasoning={candidate?.supports_reasoning ?? false}
            />
          </div>
        </div>

        <div className="card">
          <div className="card__title">Mechanisms</div>
          <MechanismPicker
            evaluators={evaluators}
            selected={methods}
            onToggle={toggle}
            applicable={applicable}
          />
          {needsJudge && (
            <div style={{ marginTop: 12 }}>
              <ModelSelect
                label="Judge model"
                models={models}
                value={judgeId}
                onChange={(id) => setJudgeId(id ?? "")}
                role="judge"
              />
            </div>
          )}
        </div>

        <button className="btn btn--primary" disabled={!canRun || loading} onClick={evaluate} style={{ width: "100%" }}>
          {loading ? "Evaluating…" : "Evaluate"}
        </button>
      </div>

      <div>
        {error && <div className="banner">{error}</div>}
        {!result && !error && (
          <div className="empty">
            Pick a prompt, a model and one or more mechanisms, then evaluate. Selecting several
            mechanisms shows how their verdicts on the same response diverge.
          </div>
        )}
        {result && (
          <>
            <div className="card">
              <div className="card__title">Model response</div>
              {result.error ? (
                <div className="banner">{result.error}</div>
              ) : (
                <div className="response">{result.response || "(empty response)"}</div>
              )}
              <div className="meta-line">
                <span>model: {result.model_id}</span>
                <span>tokens: {result.usage.total_tokens}</span>
                <span>latency: {result.usage.latency_ms} ms</span>
              </div>
            </div>
            <div className="card">
              <div className="card__title">Scores — same response, {result.scores.length} mechanism(s)</div>
              {result.scores.length === 0 ? (
                <p className="muted">No applicable mechanism produced a score.</p>
              ) : (
                <div className="cards-grid">
                  {result.scores.map((s) => (
                    <ScoreCard key={s.method} label={labelFor.get(s.method) ?? s.method} score={s} />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
