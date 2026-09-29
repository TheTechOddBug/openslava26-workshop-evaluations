// Types mirroring the backend contract (see the OpenAPI schema at /docs).

export type EvalMethod =
  | "exact_match"
  | "numeric"
  | "regex"
  | "json_schema"
  | "code_exec"
  | "sql_exec"
  | "bleu"
  | "rouge_l"
  | "fuzzy"
  | "llm_judge"
  | "llm_judge_pairwise"
  | "ensemble_judge";

export type EvalTier = "deterministic" | "similarity" | "llm_judge" | "advanced";

export type Provider = "openai_compat" | "anthropic" | "fake";

export interface ModelSpec {
  id: string;
  display_name: string;
  provider: Provider;
  model_id: string;
  base_url?: string | null;
  api_key_env?: string | null;
  role: string;
  supports_reasoning: boolean;
  enabled?: boolean;
  source?: string | null;
}

// What the management endpoint (/api/catalog/manage) returns: every model including
// disabled ones, plus whether its API key is present in the running process.
export interface ManagedModel extends ModelSpec {
  enabled: boolean;
  source: string | null;
  key_detected: boolean;
}

export interface DiscoverResponse {
  models: string[]; // model ids the endpoint reports (e.g. "qwen3:4b")
  already_added: string[]; // of those, the ones already in the catalogue
}

export interface RunParams {
  temperature: number;
  max_tokens: number;
  top_p?: number | null;
  top_k?: number | null;
  reasoning_effort?: string | null;
  seed?: number | null;
  stop?: string[] | null;
  presence_penalty?: number | null;
  frequency_penalty?: number | null;
}

export interface EvaluatorInfo {
  method: EvalMethod;
  tier: EvalTier;
  label: string;
  description: string;
  required_fields: string[];
  needs_judge: boolean;
}

export interface DatasetSummary {
  category: string;
  count: number;
  methods: string[];
}

export interface EvalCase {
  id: string;
  category: string;
  prompt: string;
  default_method: EvalMethod;
  reference?: string | null;
  tests?: string | null;
  sql_schema?: string | null;
  json_schema?: Record<string, unknown> | null;
  rubric?: string[] | null;
  subcategory?: string | null;
  lang?: string | null;
  max_tokens?: number | null;
  enabled?: boolean;
  source?: string | null;
}

// What the dataset management endpoint (/api/catalog/datasets/manage) returns: every case
// including disabled ones, each tagged with its source ("file" base or "user" overlay).
export interface ManagedCase extends EvalCase {
  enabled: boolean;
  source: string | null;
}

export interface Usage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
}

export interface Score {
  method: EvalMethod;
  value: number;
  passed?: boolean | null;
  detail: string;
  dimensions?: Record<string, number> | null;
  judge_model?: string | null;
  usage?: Usage | null;
}

export interface CellResult {
  case_id: string;
  model_id: string;
  label?: string | null;
  params: RunParams;
  response: string;
  usage: Usage;
  scores: Score[];
  error?: string | null;
}

export interface CandidateConfig {
  model_id: string;
  params?: RunParams;
  prompt_override?: string | null;
  label?: string | null;
}

export interface Run {
  id: string;
  status: string;
  results: CellResult[];
  total_cells: number;
  completed_cells: number;
  error?: string | null;
  created_at?: string | null;
}

export interface JudgeAgreement {
  pearson: number;
  spearman: number;
  rank_agreement: number;
  mae_overall: number;
  mae_by_dimension: Record<string, number>;
  verdict: string;
  sample_size: number;
}

export interface EvaluateRequest {
  model_id: string;
  methods: EvalMethod[];
  params?: RunParams;
  judge_model_id?: string | null;
  judge_params?: RunParams;
  case_id?: string | null;
  prompt_override?: string | null;
  prompt?: string | null;
  reference?: string | null;
  rubric?: string[] | null;
  tests?: string | null;
  sql_schema?: string | null;
}

export interface RunRequest {
  case_ids: string[];
  candidates: CandidateConfig[];
  methods: EvalMethod[];
  judge_model_id?: string | null;
  judge_params?: RunParams;
}

export interface JudgeAgreementRequest {
  run_id: string;
  reference_judge_model_id: string;
  sample_size?: number;
  judge_params?: RunParams;
}

export type PairwiseVerdict = "a" | "b" | "tie";

export interface PairwiseResult {
  case_id: string;
  prompt: string;
  model_a: string;
  model_b: string;
  response_a: string;
  response_b: string;
  verdict: PairwiseVerdict;
  justification: string;
  judge_model: string;
  swapped_verdict?: PairwiseVerdict | null;
  position_bias?: boolean | null;
  error?: string | null;
}

export interface CompareRequest {
  model_a: string;
  model_b: string;
  judge_model_id: string;
  params_a?: RunParams;
  params_b?: RunParams;
  prompt_override_a?: string | null;
  prompt_override_b?: string | null;
  judge_params?: RunParams;
  swap?: boolean;
  case_id?: string | null;
  prompt?: string | null;
  reference?: string | null;
}

export interface JudgeScore {
  judge_model: string;
  score: number;
  dimensions: Record<string, number>;
}

export interface EnsembleResult {
  case_id: string;
  response: string;
  per_judge: JudgeScore[];
  ensemble_score: number;
  ensemble_dimensions: Record<string, number>;
  spread: number;
  error?: string | null;
}

export interface EnsembleRequest {
  model_id: string;
  judge_model_ids: string[];
  params?: RunParams;
  prompt_override?: string | null;
  judge_params?: RunParams;
  case_id?: string | null;
  prompt?: string | null;
  reference?: string | null;
  rubric?: string[] | null;
}

export const DEFAULT_PARAMS: RunParams = {
  temperature: 0,
  max_tokens: 1024,
};
