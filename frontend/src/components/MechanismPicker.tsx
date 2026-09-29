import type { EvalMethod, EvaluatorInfo } from "../api/types";

const TIER_ORDER = ["deterministic", "similarity", "llm_judge", "advanced"] as const;
const TIER_LABEL: Record<string, string> = {
  deterministic: "Deterministic — no model needed",
  similarity: "Similarity — reference overlap",
  llm_judge: "LLM as judge",
  advanced: "Advanced",
};

export function MechanismPicker({
  evaluators,
  selected,
  onToggle,
  applicable,
}: {
  evaluators: EvaluatorInfo[];
  selected: Set<EvalMethod>;
  onToggle: (method: EvalMethod) => void;
  applicable: Set<string> | null; // null = every mechanism applies
}) {
  const groups = TIER_ORDER.map((tier) => ({
    tier,
    items: evaluators.filter((e) => e.tier === tier),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="checklist">
      {groups.map(({ tier, items }) => (
        <div key={tier}>
          <div className="tier-label">{TIER_LABEL[tier] ?? tier}</div>
          {items.map((ev) => {
            const isApplicable = applicable === null || applicable.has(ev.method);
            const on = selected.has(ev.method);
            return (
              <label
                key={ev.method}
                className={`check ${on ? "check--on" : ""} ${isApplicable ? "" : "check--disabled"}`}
                title={isApplicable ? ev.description : "This case has no reference field for this mechanism"}
              >
                <input
                  type="checkbox"
                  checked={on}
                  disabled={!isApplicable}
                  onChange={() => onToggle(ev.method)}
                />
                <span>
                  <span className="check__label">{ev.label}</span>
                  <br />
                  <span className="check__desc">{ev.description}</span>
                </span>
              </label>
            );
          })}
        </div>
      ))}
    </div>
  );
}
