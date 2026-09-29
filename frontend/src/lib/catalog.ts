import type { ModelSpec } from "../api/types";

export const isJudge = (m: ModelSpec) => m.role === "judge" || m.role === "both";
export const isCandidate = (m: ModelSpec) => m.role === "candidate" || m.role === "both";

// Prefer a non-reasoning judge by default: reasoning models tend to spend their whole
// token budget thinking and never emit the rubric JSON.
export function defaultJudgeId(models: ModelSpec[]): string {
  const judges = models.filter(isJudge);
  return (judges.find((m) => !m.supports_reasoning) ?? judges[0])?.id ?? "";
}

export function defaultCandidateId(models: ModelSpec[]): string {
  return (models.find(isCandidate) ?? models[0])?.id ?? "";
}

// Turn a provider model id (e.g. "qwen3:4b") into a catalogue id ("qwen3-4b").
// Mirrors the backend's sanitize_id so a discovered model gets the same id here.
export function sanitizeId(modelId: string): string {
  const parts = modelId
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "-")
    .split("-")
    .filter(Boolean);
  return parts.join("-") || "model";
}
