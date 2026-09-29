"""HTTP routes. Services are resolved from the application container on app.state."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from workshop_evals.adapters.inbound.http.dto import (
    CompareRequest,
    CredentialRequest,
    DiscoverRequest,
    EnabledRequest,
    EnsembleRequest,
    EvaluateRequest,
    JudgeAgreementRequest,
    RunRequest,
)
from workshop_evals.domain.models import (
    CellResult,
    EnsembleResult,
    EvalCase,
    JudgeAgreement,
    MatrixSpec,
    ModelSpec,
    PairwiseResult,
    Run,
)


def _resolve_case(container, case_id, build_inline):
    if case_id is not None:
        case = container.datasets.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"unknown case '{case_id}'")
        return case
    try:
        return build_inline()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


router = APIRouter(prefix="/api")


def _container(request: Request):
    return request.app.state.container


@router.get("/catalog/models", response_model=list[ModelSpec])
def list_models(request: Request) -> list[ModelSpec]:
    return _container(request).catalog.list_models()


@router.get("/catalog/evaluators")
def list_evaluators(request: Request) -> list[dict]:
    return _container(request).catalog.list_evaluators()


@router.get("/catalog/datasets")
def list_datasets(request: Request) -> list[dict]:
    return [s.__dict__ for s in _container(request).catalog.list_datasets()]


@router.get("/catalog/datasets/{category}/cases", response_model=list[EvalCase])
def list_cases(category: str, request: Request) -> list[EvalCase]:
    return _container(request).datasets.get_cases(category)


@router.get("/catalog/cases/{case_id}/methods")
def applicable_methods(case_id: str, request: Request) -> list[str]:
    c = _container(request)
    if c.datasets.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown case '{case_id}'")
    return [m.value for m in c.catalog.applicable_methods(case_id)]


@router.post("/evaluate", response_model=CellResult)
async def evaluate(req: EvaluateRequest, request: Request) -> CellResult:
    c = _container(request)
    if req.case_id is not None:
        case = c.datasets.get_case(req.case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"unknown case '{req.case_id}'")
    else:
        try:
            case = req.build_inline_case()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await c.runs.evaluate_cell(
        case, req.as_candidate(), req.methods, req.judge_model_id, req.judge_params
    )


@router.post("/runs", response_model=Run, status_code=202)
async def create_run(req: RunRequest, request: Request, background: BackgroundTasks) -> Run:
    spec = MatrixSpec(
        case_ids=req.case_ids,
        candidates=req.candidates,
        methods=req.methods,
        judge_model_id=req.judge_model_id,
        judge_params=req.judge_params,
    )
    service = _container(request).runs
    run = service.create_run(spec)
    background.add_task(service.execute_run, run.id)
    return run


@router.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str, request: Request) -> Run:
    run = _container(request).run_repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"unknown run '{run_id}'")
    return run


@router.post("/judge-agreement", response_model=JudgeAgreement)
async def judge_agreement(req: JudgeAgreementRequest, request: Request) -> JudgeAgreement:
    service = _container(request).judge_agreement
    try:
        return await service.compare_on_run(
            req.run_id, req.reference_judge_model_id, req.sample_size, req.judge_params
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/compare", response_model=PairwiseResult)
async def compare(req: CompareRequest, request: Request) -> PairwiseResult:
    c = _container(request)
    case = _resolve_case(c, req.case_id, req.build_inline_case)
    return await c.compare.compare(
        case,
        req.candidate_a(),
        req.candidate_b(),
        req.judge_model_id,
        req.judge_params,
        req.swap,
    )


@router.post("/ensemble-judge", response_model=EnsembleResult)
async def ensemble_judge(req: EnsembleRequest, request: Request) -> EnsembleResult:
    c = _container(request)
    if not req.judge_model_ids:
        raise HTTPException(status_code=422, detail="at least one judge model is required")
    case = _resolve_case(c, req.case_id, req.build_inline_case)
    return await c.ensemble.judge(case, req.candidate(), req.judge_model_ids, req.judge_params)


# --- model catalogue management -------------------------------------------


@router.get("/catalog/manage")
def manage_models(request: Request) -> list[dict]:
    return _container(request).models_mgmt.list_all()


@router.post("/catalog/discover")
async def discover_models(req: DiscoverRequest, request: Request) -> dict:
    try:
        return await _container(request).models_mgmt.discover(req.base_url)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"could not reach {req.base_url}: {type(exc).__name__}"
        ) from exc


@router.post("/catalog/models")
def upsert_model(spec: ModelSpec, request: Request) -> dict:
    return _container(request).models_mgmt.upsert(spec)


@router.delete("/catalog/models/{model_id}")
def delete_model(model_id: str, request: Request) -> dict:
    if not _container(request).models_mgmt.remove(model_id):
        raise HTTPException(
            status_code=400, detail="base models cannot be deleted; disable it instead"
        )
    return {"removed": True}


@router.post("/catalog/models/{model_id}/enabled")
def set_model_enabled(model_id: str, req: EnabledRequest, request: Request) -> dict:
    result = _container(request).models_mgmt.set_enabled(model_id, req.enabled)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown model '{model_id}'")
    return result


@router.post("/catalog/credentials")
def set_credential(req: CredentialRequest, request: Request) -> dict:
    try:
        _container(request).models_mgmt.set_credential(req.env_name, req.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"env_name": req.env_name, "detected": True}


# --- dataset catalogue management ------------------------------------------


@router.get("/catalog/datasets/manage")
def manage_cases(request: Request) -> list[dict]:
    return _container(request).datasets_mgmt.list_all()


@router.post("/catalog/cases")
def upsert_case(case: EvalCase, request: Request) -> dict:
    return _container(request).datasets_mgmt.upsert(case)


@router.delete("/catalog/cases/{case_id}")
def delete_case(case_id: str, request: Request) -> dict:
    if not _container(request).datasets_mgmt.remove(case_id):
        raise HTTPException(
            status_code=400, detail="base cases cannot be deleted; disable it instead"
        )
    return {"removed": True}


@router.post("/catalog/cases/{case_id}/enabled")
def set_case_enabled(case_id: str, req: EnabledRequest, request: Request) -> dict:
    result = _container(request).datasets_mgmt.set_enabled(case_id, req.enabled)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown case '{case_id}'")
    return result
