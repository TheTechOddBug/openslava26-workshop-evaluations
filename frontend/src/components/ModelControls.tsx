import type { ModelSpec, RunParams } from "../api/types";

export function ModelSelect({
  label,
  models,
  value,
  onChange,
  role,
  allowNone,
}: {
  label: string;
  models: ModelSpec[];
  value: string | null;
  onChange: (id: string | null) => void;
  role: "candidate" | "judge";
  allowNone?: boolean;
}) {
  const usable = models.filter((m) =>
    role === "judge" ? m.role === "judge" || m.role === "both" : m.role === "candidate" || m.role === "both",
  );
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
      >
        {allowNone && <option value="">None</option>}
        {usable.map((m) => (
          <option key={m.id} value={m.id}>
            {m.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ParamControls({
  params,
  onChange,
  supportsReasoning,
}: {
  params: RunParams;
  onChange: (params: RunParams) => void;
  supportsReasoning: boolean;
}) {
  const set = (patch: Partial<RunParams>) => onChange({ ...params, ...patch });
  return (
    <div className="stack">
      <label className="field">
        <span className="field__label">Temperature: {params.temperature.toFixed(2)}</span>
        <input
          type="range"
          min={0}
          max={2}
          step={0.05}
          value={params.temperature}
          onChange={(e) => set({ temperature: Number(e.target.value) })}
        />
      </label>

      <label className="field">
        <span className="field__label">Max tokens</span>
        <input
          type="number"
          min={1}
          max={8192}
          value={params.max_tokens}
          onChange={(e) => set({ max_tokens: Number(e.target.value) })}
        />
      </label>

      {supportsReasoning && (
        <label className="field">
          <span className="field__label">Reasoning effort</span>
          <select
            value={params.reasoning_effort ?? "none"}
            onChange={(e) => set({ reasoning_effort: e.target.value === "none" ? null : e.target.value })}
          >
            <option value="none">None</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
      )}
    </div>
  );
}
