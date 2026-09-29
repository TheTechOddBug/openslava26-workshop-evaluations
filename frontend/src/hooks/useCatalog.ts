import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import type { DatasetSummary, EvaluatorInfo, ModelSpec } from "../api/types";

export interface Catalog {
  models: ModelSpec[];
  evaluators: EvaluatorInfo[];
  datasets: DatasetSummary[];
}

export function useCatalog() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reloadable so the Models tab can refresh the selectors after adding,
  // enabling or removing a model.
  const refresh = useCallback(() => {
    Promise.all([api.listModels(), api.listEvaluators(), api.listDatasets()])
      .then(([models, evaluators, datasets]) => setCatalog({ models, evaluators, datasets }))
      .catch((err: unknown) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Cannot reach the backend. Start it with uvicorn on port 8000.",
        ),
      );
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { catalog, error, refresh };
}
