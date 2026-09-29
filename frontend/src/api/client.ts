import type {
  CellResult,
  CompareRequest,
  DatasetSummary,
  DiscoverResponse,
  EnsembleRequest,
  EnsembleResult,
  EvalCase,
  EvaluateRequest,
  EvaluatorInfo,
  JudgeAgreement,
  JudgeAgreementRequest,
  ManagedCase,
  ManagedModel,
  ModelSpec,
  PairwiseResult,
  Run,
  RunRequest,
} from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body; keep the status text
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

const get = <T>(path: string) => request<T>(path);
const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });
const del = <T>(path: string) => request<T>(path, { method: "DELETE" });

export const api = {
  listModels: () => get<ModelSpec[]>("/api/catalog/models"),
  listEvaluators: () => get<EvaluatorInfo[]>("/api/catalog/evaluators"),
  listDatasets: () => get<DatasetSummary[]>("/api/catalog/datasets"),
  listCases: (category: string) =>
    get<EvalCase[]>(`/api/catalog/datasets/${encodeURIComponent(category)}/cases`),
  applicableMethods: (caseId: string) =>
    get<string[]>(`/api/catalog/cases/${encodeURIComponent(caseId)}/methods`),
  evaluate: (req: EvaluateRequest) => post<CellResult>("/api/evaluate", req),
  createRun: (req: RunRequest) => post<Run>("/api/runs", req),
  getRun: (runId: string) => get<Run>(`/api/runs/${encodeURIComponent(runId)}`),
  judgeAgreement: (req: JudgeAgreementRequest) =>
    post<JudgeAgreement>("/api/judge-agreement", req),
  compare: (req: CompareRequest) => post<PairwiseResult>("/api/compare", req),
  ensembleJudge: (req: EnsembleRequest) => post<EnsembleResult>("/api/ensemble-judge", req),

  // Model catalogue management
  manageModels: () => get<ManagedModel[]>("/api/catalog/manage"),
  discoverModels: (baseUrl: string) =>
    post<DiscoverResponse>("/api/catalog/discover", { base_url: baseUrl }),
  upsertModel: (spec: ModelSpec) => post<ManagedModel>("/api/catalog/models", spec),
  deleteModel: (id: string) =>
    del<{ removed: boolean }>(`/api/catalog/models/${encodeURIComponent(id)}`),
  setModelEnabled: (id: string, enabled: boolean) =>
    post<ManagedModel>(`/api/catalog/models/${encodeURIComponent(id)}/enabled`, { enabled }),
  setCredential: (envName: string, value: string) =>
    post<{ env_name: string; detected: boolean }>("/api/catalog/credentials", {
      env_name: envName,
      value,
    }),

  // Dataset catalogue management
  manageCases: () => get<ManagedCase[]>("/api/catalog/datasets/manage"),
  upsertCase: (c: EvalCase) => post<ManagedCase>("/api/catalog/cases", c),
  deleteCase: (id: string) =>
    del<{ removed: boolean }>(`/api/catalog/cases/${encodeURIComponent(id)}`),
  setCaseEnabled: (id: string, enabled: boolean) =>
    post<ManagedCase>(`/api/catalog/cases/${encodeURIComponent(id)}/enabled`, { enabled }),
};
