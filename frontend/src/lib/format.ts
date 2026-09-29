export type Tone = "pass" | "partial" | "fail";

export function tone(value: number): Tone {
  if (value >= 0.7) return "pass";
  if (value >= 0.4) return "partial";
  return "fail";
}

export const fmt = (v: number, digits = 2) => v.toFixed(digits);

export const JUDGE_DIMENSIONS = [
  "correctness",
  "completeness",
  "robustness",
  "clarity",
  "efficiency",
] as const;
