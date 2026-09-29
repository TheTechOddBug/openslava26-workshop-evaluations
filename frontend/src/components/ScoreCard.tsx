import type { Score } from "../api/types";
import { JUDGE_DIMENSIONS, fmt, tone } from "../lib/format";

function statusChip(score: Score) {
  if (score.passed === true) return { cls: "chip--pass", text: "pass" };
  if (score.passed === false) return { cls: "chip--fail", text: "fail" };
  return { cls: `chip--${tone(score.value)}`, text: score.value >= 0.5 ? "partial" : "low" };
}

export function ScoreCard({ label, score }: { label: string; score: Score }) {
  const t = tone(score.value);
  const chip = statusChip(score);
  const dims = score.dimensions;

  return (
    <div className="score-card">
      <div className="score-card__head">
        <span className="score-card__method">{label}</span>
        <span className={`chip ${chip.cls}`}>{chip.text}</span>
      </div>

      <div className="row">
        <div className="scorebar" style={{ flex: 1 }}>
          <div
            className="scorebar__fill"
            style={{ width: `${Math.max(0, Math.min(1, score.value)) * 100}%`, background: `var(--${t})` }}
          />
        </div>
        <span className="score-card__value">{fmt(score.value)}</span>
      </div>

      {dims && (
        <div className="dims">
          {JUDGE_DIMENSIONS.filter((d) => dims[d] !== undefined).map((d) => (
            <Dimension key={d} name={d} value={dims[d]} />
          ))}
        </div>
      )}

      {score.judge_model && <div className="score-card__detail">Judge: {score.judge_model}</div>}
      {score.detail && <div className="score-card__detail">{score.detail}</div>}
    </div>
  );
}

function Dimension({ name, value }: { name: string; value: number }) {
  return (
    <>
      <span className="dims__name">{name}</span>
      <div className="scorebar">
        <div
          className="scorebar__fill"
          style={{ width: `${(Math.max(0, Math.min(10, value)) / 10) * 100}%`, background: "var(--accent)" }}
        />
      </div>
      <span className="dims__value">{value.toFixed(0)}</span>
    </>
  );
}
