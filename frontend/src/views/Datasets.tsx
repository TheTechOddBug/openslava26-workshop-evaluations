import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, api } from "../api/client";
import type { Catalog } from "../hooks/useCatalog";
import type { EvalCase, EvalMethod, ManagedCase } from "../api/types";

interface FormState {
  id: string;
  category: string;
  prompt: string;
  default_method: EvalMethod;
  reference: string;
  rubric: string; // one per line
  tests: string;
  sql_schema: string;
}

const EMPTY_FORM: FormState = {
  id: "",
  category: "",
  prompt: "",
  default_method: "llm_judge",
  reference: "",
  rubric: "",
  tests: "",
  sql_schema: "",
};

/**
 * Browse and edit the evaluation cases the rest of the app runs against. The shipped JSONL
 * dataset is read-only (source "file"); anything added or edited here is written to a
 * gitignored overlay (source "user") and immediately available in the other tabs. Base cases
 * can be disabled but not deleted.
 */
export function Datasets({ catalog, onChange }: { catalog: Catalog; onChange: () => void }) {
  const { evaluators } = catalog;
  const [cases, setCases] = useState<ManagedCase[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingBase, setEditingBase] = useState<ManagedCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      setCases(await api.manageCases());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cannot load the datasets.");
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const categories = useMemo(() => [...new Set(cases.map((c) => c.category))].sort(), [cases]);
  useEffect(() => {
    if (!filter && categories.length) setFilter(categories[0]);
  }, [categories, filter]);

  const methodLabel = useMemo(
    () => new Map(evaluators.map((e) => [e.method, e.label] as const)),
    [evaluators],
  );

  const shown = cases.filter((c) => !filter || c.category === filter);
  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));

  // Which mechanisms the fields currently filled in would enable (mirrors the backend rule).
  const present = new Set<string>();
  if (form.reference.trim()) present.add("reference");
  if (form.rubric.trim()) present.add("rubric");
  if (form.tests.trim()) present.add("tests");
  if (form.sql_schema.trim()) present.add("sql_schema");
  const applicable = evaluators
    .filter((e) => e.required_fields.every((f) => present.has(f)))
    .map((e) => e.label);

  function toCase(): EvalCase {
    const rubric = form.rubric
      .split("\n")
      .map((r) => r.trim())
      .filter(Boolean);
    return {
      ...(editingBase ?? {}), // preserve fields the form doesn't expose (json_schema, lang, …)
      id: form.id.trim(),
      category: form.category.trim(),
      prompt: form.prompt,
      default_method: form.default_method,
      reference: form.reference.trim() || null,
      rubric: rubric.length ? rubric : null,
      tests: form.tests.trim() || null,
      sql_schema: form.sql_schema.trim() || null,
    };
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const c = toCase();
    if (!c.id || !c.category || !c.prompt.trim()) {
      setError("id, category and prompt are required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.upsertCase(c);
      await reload();
      onChange();
      setForm(EMPTY_FORM);
      setEditingBase(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the case.");
    } finally {
      setBusy(false);
    }
  }

  function edit(c: ManagedCase) {
    setEditingBase(c);
    setForm({
      id: c.id,
      category: c.category,
      prompt: c.prompt,
      default_method: c.default_method,
      reference: c.reference ?? "",
      rubric: (c.rubric ?? []).join("\n"),
      tests: c.tests ?? "",
      sql_schema: c.sql_schema ?? "",
    });
  }

  function cancelEdit() {
    setEditingBase(null);
    setForm(EMPTY_FORM);
  }

  async function toggleEnabled(c: ManagedCase) {
    setBusy(true);
    setError(null);
    try {
      await api.setCaseEnabled(c.id, !c.enabled);
      await reload();
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update the case.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(c: ManagedCase) {
    setBusy(true);
    setError(null);
    try {
      await api.deleteCase(c.id);
      if (editingBase?.id === c.id) cancelEdit();
      await reload();
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove the case.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="split">
      <div>
        <div className="card">
          <div className="card__title">{editingBase ? `Edit ${editingBase.id}` : "Add a case"}</div>
          <form className="stack" onSubmit={save}>
            <label className="field">
              <span className="field__label">Case id</span>
              <input
                type="text"
                value={form.id}
                onChange={(e) => set({ id: e.target.value })}
                placeholder="my-case-01"
                disabled={!!editingBase}
              />
            </label>
            <label className="field">
              <span className="field__label">Category</span>
              <input
                type="text"
                list="ds-categories"
                value={form.category}
                onChange={(e) => set({ category: e.target.value })}
                placeholder="an existing category or a new one"
              />
              <datalist id="ds-categories">
                {categories.map((c) => (
                  <option key={c} value={c} />
                ))}
              </datalist>
            </label>
            <label className="field">
              <span className="field__label">Prompt</span>
              <textarea value={form.prompt} onChange={(e) => set({ prompt: e.target.value })} />
            </label>
            <label className="field">
              <span className="field__label">Default mechanism</span>
              <select
                value={form.default_method}
                onChange={(e) => set({ default_method: e.target.value as EvalMethod })}
              >
                {evaluators.map((ev) => (
                  <option key={ev.method} value={ev.method}>
                    {ev.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field__label">Reference answer (exact / similarity)</span>
              <input
                type="text"
                value={form.reference}
                onChange={(e) => set({ reference: e.target.value })}
                placeholder="'|' separates accepted variants"
              />
            </label>
            <label className="field">
              <span className="field__label">Judge rubric, one per line</span>
              <textarea
                value={form.rubric}
                onChange={(e) => set({ rubric: e.target.value })}
                style={{ minHeight: 64 }}
              />
            </label>
            <label className="field">
              <span className="field__label">Tests — Python asserts, for code execution</span>
              <textarea
                value={form.tests}
                onChange={(e) => set({ tests: e.target.value })}
                style={{ minHeight: 64 }}
              />
            </label>
            <label className="field">
              <span className="field__label">SQL schema — DDL + seed, for SQL execution</span>
              <textarea
                value={form.sql_schema}
                onChange={(e) => set({ sql_schema: e.target.value })}
                style={{ minHeight: 64 }}
              />
            </label>
            <span className="field__hint">
              Enables: {applicable.join(", ") || "—"} (add a reference, rubric, tests or SQL
              schema to unlock more mechanisms)
            </span>
            <div className="row">
              <button className="btn btn--primary" type="submit" disabled={busy}>
                {editingBase ? "Save changes" : "Add case"}
              </button>
              {editingBase && (
                <button className="btn" type="button" onClick={cancelEdit}>
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>
      </div>

      <div>
        {error && <div className="banner">{error}</div>}
        <div className="card">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
            <div className="card__title" style={{ margin: 0 }}>
              Cases — {shown.length}
            </div>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{ width: "auto" }}
              aria-label="Filter by category"
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="matrix">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Mechanism</th>
                  <th>Source</th>
                  <th>On</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {shown.map((c) => (
                  <tr key={c.id}>
                    <td className="case">
                      <div className="mono" style={{ fontSize: 12 }}>
                        {c.id}
                      </div>
                      <div
                        style={{
                          color: "var(--muted)",
                          fontSize: 12,
                          maxWidth: 360,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {c.prompt}
                      </div>
                    </td>
                    <td>{methodLabel.get(c.default_method) ?? c.default_method}</td>
                    <td>
                      <span className={`chip ${c.source === "user" ? "chip--partial" : "chip--neutral"}`}>
                        {c.source ?? "file"}
                      </span>
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={c.enabled}
                        disabled={busy}
                        aria-label={`Enable ${c.id}`}
                        onChange={() => toggleEnabled(c)}
                      />
                    </td>
                    <td>
                      <div className="row">
                        <button className="btn" disabled={busy} onClick={() => edit(c)}>
                          Edit
                        </button>
                        <button
                          className="btn"
                          title={
                            c.source === "user"
                              ? "Remove"
                              : "Base cases can't be deleted — disable them instead"
                          }
                          disabled={busy || c.source !== "user"}
                          onClick={() => remove(c)}
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
