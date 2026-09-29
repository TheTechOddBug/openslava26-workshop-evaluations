from workshop_evals.adapters.outbound.demo_client import make_demo_client
from workshop_evals.domain.models import ModelSpec, Provider, RunParams
from workshop_evals.domain.scoring.judge_rubric import JUDGE_SYSTEM, parse_judge_response


def _model() -> ModelSpec:
    return ModelSpec(id="m", display_name="m", provider=Provider.FAKE, model_id="x")


async def test_demo_returns_fixed_candidate_reply():
    client = make_demo_client()
    out = await client.chat(_model(), [{"role": "user", "content": "classify this"}], RunParams())
    assert out.text == "positive"
    assert out.error is None


async def test_demo_returns_parseable_judge_reply():
    client = make_demo_client()
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": "grade this"},
    ]
    out = await client.chat(_model(), messages, RunParams())
    score, _justification, dims = parse_judge_response(out.text, "test")
    assert 0.0 <= score <= 1.0
    assert len(dims) == 5
