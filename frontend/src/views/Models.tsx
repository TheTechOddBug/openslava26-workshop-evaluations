import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, api } from "../api/client";
import type { ManagedModel, ModelSpec, Provider } from "../api/types";
import { sanitizeId } from "../lib/catalog";

const OLLAMA_DEFAULT = "http://localhost:11434/v1";

interface FormState {
  id: string;
  display_name: string;
  provider: Provider;
  model_id: string;
  base_url: string;
  api_key_env: string;
  role: string;
  supports_reasoning: boolean;
  enabled: boolean;
}

const EMPTY_FORM: FormState = {
  id: "",
  display_name: "",
  provider: "openai_compat",
  model_id: "",
  base_url: OLLAMA_DEFAULT,
  api_key_env: "",
  role: "both",
  supports_reasoning: false,
  enabled: true,
};

function toSpec(f: FormState): ModelSpec {
  return {
    id: f.id.trim(),
    display_name: f.display_name.trim() || f.id.trim(),
    provider: f.provider,
    model_id: f.model_id.trim(),
    base_url: f.base_url.trim() || null,
    api_key_env: f.api_key_env.trim() || null,
    role: f.role,
    supports_reasoning: f.supports_reasoning,
    enabled: f.enabled,
  };
}

/**
 * Manage the model catalogue without leaving the app. Three ways in, all optional:
 * discover what a local server already serves, add or edit an entry by hand (local or
 * remote), and supply an API key for the running session. Whatever ends up here feeds
 * the selectors on every other tab. Nothing configured in the YAML files needs any of
 * this — it is only for what the files do not already cover.
 */
export function Models({ onChange }: { onChange: () => void }) {
  const [models, setModels] = useState<ManagedModel[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [baseUrl, setBaseUrl] = useState(OLLAMA_DEFAULT);
  const [discovered, setDiscovered] = useState<string[] | null>(null);
  const [discovering, setDiscovering] = useState(false);

  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editing, setEditing] = useState<string | null>(null);

  const [envName, setEnvName] = useState("");
  const [keyValue, setKeyValue] = useState("");
  const [credMsg, setCredMsg] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setModels(await api.manageModels());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cannot load the model catalogue.");
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  // A model already exists when the catalogue holds its provider model id.
  const knownModelIds = useMemo(() => new Set(models.map((m) => m.model_id)), [models]);

  // Distinct API-key variables the configured models reference (any provider), each with
  // whether it is currently set. Lets the user set exactly what the catalogue needs.
  const referencedKeys = useMemo(() => {
    const status = new Map<string, boolean>();
    for (const m of models) {
      if (m.api_key_env) {
        status.set(m.api_key_env, (status.get(m.api_key_env) ?? false) || m.key_detected);
      }
    }
    return [...status.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [models]);

  // After any change: refresh this list and the shared catalogue the other tabs read.
  const afterMutation = async () => {
    await reload();
    onChange();
  };

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));

  async function discover() {
    setDiscovering(true);
    setError(null);
    setDiscovered(null);
    try {
      const res = await api.discoverModels(baseUrl);
      setDiscovered(res.models);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : `Could not reach ${baseUrl}. Is the server running?`,
      );
    } finally {
      setDiscovering(false);
    }
  }

  async function save(spec: ModelSpec): Promise<boolean> {
    if (!spec.id || !spec.model_id) {
      setError("An id and a model id are required.");
      return false;
    }
    setBusy(true);
    setError(null);
    try {
      await api.upsertModel(spec);
      await afterMutation();
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the model.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function addDiscovered(rawId: string) {
    await save({
      id: sanitizeId(rawId),
      display_name: `${rawId} (local)`,
      provider: "openai_compat",
      model_id: rawId,
      base_url: baseUrl,
      api_key_env: null,
      role: "both",
      supports_reasoning: false,
      enabled: true,
    });
  }

  async function submitForm(e: React.FormEvent) {
    e.preventDefault();
    if (await save(toSpec(form))) {
      setForm(EMPTY_FORM);
      setEditing(null);
    }
  }

  function edit(m: ManagedModel) {
    setEditing(m.id);
    setForm({
      id: m.id,
      display_name: m.display_name,
      provider: m.provider === "anthropic" ? "anthropic" : "openai_compat",
      model_id: m.model_id,
      base_url: m.base_url ?? "",
      api_key_env: m.api_key_env ?? "",
      role: m.role,
      supports_reasoning: m.supports_reasoning,
      enabled: m.enabled,
    });
  }

  function cancelEdit() {
    setEditing(null);
    setForm(EMPTY_FORM);
  }

  async function toggleEnabled(m: ManagedModel) {
    setBusy(true);
    setError(null);
    try {
      await api.setModelEnabled(m.id, !m.enabled);
      await afterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update the model.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(m: ManagedModel) {
    setBusy(true);
    setError(null);
    try {
      await api.deleteModel(m.id);
      if (editing === m.id) cancelEdit();
      await afterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove the model.");
    } finally {
      setBusy(false);
    }
  }

  async function saveCredential(e: React.FormEvent) {
    e.preventDefault();
    setCredMsg(null);
    setError(null);
    try {
      const res = await api.setCredential(envName.trim(), keyValue);
      setCredMsg(`${res.env_name} set for this session.`);
      setKeyValue("");
      await afterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not set the credential.");
    }
  }

  return (
    <div className="split">
      <div>
        <div className="card">
          <div className="card__title">Discover local models</div>
          <div className="stack">
            <label className="field">
              <span className="field__label">Server base URL (OpenAI-compatible)</span>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={OLLAMA_DEFAULT}
              />
            </label>
            <span className="field__hint">
              Asks the server which models it serves — no AI, just its <span className="mono">/models</span>{" "}
              endpoint.
            </span>
            <button className="btn" disabled={discovering || !baseUrl.trim()} onClick={discover}>
              {discovering ? "Discovering…" : "Discover models"}
            </button>
          </div>

          {discovered && discovered.length === 0 && (
            <p className="muted" style={{ marginTop: 12 }}>
              The server reported no models.
            </p>
          )}
          {discovered && discovered.length > 0 && (
            <div className="checklist" style={{ marginTop: 12 }}>
              {discovered.map((rawId) => {
                const added = knownModelIds.has(rawId);
                return (
                  <div key={rawId} className="check check--on" style={{ justifyContent: "space-between" }}>
                    <span className="mono">{rawId}</span>
                    {added ? (
                      <span className="chip chip--neutral">added</span>
                    ) : (
                      <button className="btn" disabled={busy} onClick={() => addDiscovered(rawId)}>
                        Add
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card__title">{editing ? `Edit ${editing}` : "Add a model"}</div>
          <form className="stack" onSubmit={submitForm}>
            <label className="field">
              <span className="field__label">Catalogue id</span>
              <input
                type="text"
                value={form.id}
                onChange={(e) => set({ id: e.target.value })}
                placeholder="my-model"
                disabled={!!editing}
              />
            </label>
            <label className="field">
              <span className="field__label">Display name</span>
              <input
                type="text"
                value={form.display_name}
                onChange={(e) => set({ display_name: e.target.value })}
                placeholder="My Model"
              />
            </label>
            <label className="field">
              <span className="field__label">Provider</span>
              <select
                value={form.provider}
                onChange={(e) => set({ provider: e.target.value as Provider })}
              >
                <option value="openai_compat">
                  OpenAI-compatible (Ollama, OpenAI, Google Gemini, Mistral, …)
                </option>
                <option value="anthropic">Anthropic</option>
              </select>
            </label>
            <label className="field">
              <span className="field__label">Provider model id</span>
              <input
                type="text"
                value={form.model_id}
                onChange={(e) => set({ model_id: e.target.value })}
                placeholder="llama3.2:3b"
              />
            </label>
            {form.provider === "openai_compat" && (
              <>
                <label className="field">
                  <span className="field__label">Base URL</span>
                  <input
                    type="text"
                    value={form.base_url}
                    onChange={(e) => set({ base_url: e.target.value })}
                    placeholder={OLLAMA_DEFAULT}
                  />
                </label>
                <span className="field__hint">
                  e.g. http://localhost:11434/v1 (Ollama) · https://api.openai.com/v1 ·
                  https://generativelanguage.googleapis.com/v1beta/openai (Gemini)
                </span>
              </>
            )}
            <label className="field">
              <span className="field__label">API key variable (remote models)</span>
              <input
                type="text"
                value={form.api_key_env}
                onChange={(e) => set({ api_key_env: e.target.value })}
                placeholder="e.g. OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY — empty for local"
              />
            </label>
            <label className="field">
              <span className="field__label">Role</span>
              <select value={form.role} onChange={(e) => set({ role: e.target.value })}>
                <option value="both">Candidate and judge</option>
                <option value="candidate">Candidate only</option>
                <option value="judge">Judge only</option>
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={form.supports_reasoning}
                onChange={(e) => set({ supports_reasoning: e.target.checked })}
              />
              <span className="check__label">Reasoning model</span>
            </label>
            <div className="row">
              <button className="btn btn--primary" type="submit" disabled={busy}>
                {editing ? "Save changes" : "Add model"}
              </button>
              {editing && (
                <button className="btn" type="button" onClick={cancelEdit}>
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>

        <div className="card">
          <div className="card__title">Session credentials</div>
          {referencedKeys.length > 0 && (
            <div className="stack" style={{ marginBottom: 12 }}>
              <span className="field__label">Keys your models use</span>
              <div className="checklist">
                {referencedKeys.map(([env, detected]) => (
                  <div
                    key={env}
                    className={`check ${envName === env ? "check--on" : ""}`}
                    style={{ justifyContent: "space-between", cursor: "pointer" }}
                    onClick={() => setEnvName(env)}
                  >
                    <span className="mono">{env}</span>
                    <span className={`chip ${detected ? "chip--pass" : "chip--partial"}`}>
                      {detected ? "set" : "missing"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <form className="stack" onSubmit={saveCredential}>
            <label className="field">
              <span className="field__label">Key variable</span>
              <input
                type="text"
                value={envName}
                onChange={(e) => setEnvName(e.target.value)}
                placeholder="OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY…"
              />
            </label>
            <label className="field">
              <span className="field__label">Value</span>
              <input
                type="password"
                value={keyValue}
                onChange={(e) => setKeyValue(e.target.value)}
                placeholder="paste the key"
              />
            </label>
            <span className="field__hint">
              Works for any cloud provider (OpenAI, Anthropic, Google Gemini, …). Kept in memory
              for this session only — never written to disk; set it in the environment before
              launching for a permanent one.
            </span>
            <button className="btn" type="submit" disabled={!envName.trim() || !keyValue}>
              Set for this session
            </button>
            {credMsg && <span className="chip chip--pass">{credMsg}</span>}
          </form>
        </div>
      </div>

      <div>
        {error && <div className="banner">{error}</div>}
        <div className="card">
          <div className="card__title">Catalogue — {models.length} models</div>
          <div className="matrix">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Role</th>
                  <th>Source</th>
                  <th>API key</th>
                  <th>Enabled</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.id}>
                    <td className="case">
                      <div>{m.display_name}</div>
                      <div className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
                        {m.model_id}
                      </div>
                    </td>
                    <td>{m.role}</td>
                    <td>
                      <span className={`chip ${m.source === "user" ? "chip--partial" : "chip--neutral"}`}>
                        {m.source ?? "file"}
                      </span>
                    </td>
                    <td>
                      <KeyChip model={m} />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={m.enabled}
                        disabled={busy}
                        aria-label={`Enable ${m.display_name}`}
                        onChange={() => toggleEnabled(m)}
                      />
                    </td>
                    <td>
                      <div className="row">
                        <button
                          className="btn"
                          title="Edit"
                          disabled={busy}
                          onClick={() => edit(m)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn"
                          title={
                            m.source === "user"
                              ? "Remove"
                              : "Base models can't be deleted — disable them instead"
                          }
                          disabled={busy || m.source !== "user"}
                          onClick={() => remove(m)}
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

function KeyChip({ model }: { model: ManagedModel }) {
  if (!model.api_key_env) return <span className="chip chip--neutral">not needed</span>;
  return model.key_detected ? (
    <span className="chip chip--pass">key set</span>
  ) : (
    <span className="chip chip--partial">no key</span>
  );
}
