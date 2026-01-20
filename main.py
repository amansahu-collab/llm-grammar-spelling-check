from fastapi import FastAPI, HTTPException
import httpx
import yaml
from pathlib import Path
import asyncio
from pydantic import BaseModel

from aggregators.content import ContentAggregator
from aggregators.language import LanguageAggregator

app = FastAPI(title="Scoring Orchestrator")

BASE_DIR = Path(__file__).parent


# --------------------
# Request model
# --------------------
class ScoreRequest(BaseModel):
    test_type: str
    passage: str
    summary: str


# --------------------
# Load configs once
# --------------------
with open(BASE_DIR / "services" / "content.yaml") as f:
    CONTENT_SERVICE = yaml.safe_load(f)

with open(BASE_DIR / "services" / "language.yaml") as f:
    LANGUAGE_SERVICE = yaml.safe_load(f)

SERVICES = {
    "content": CONTENT_SERVICE,
    "language": LANGUAGE_SERVICE
}

AGGREGATORS = {
    "content": ContentAggregator(),
    "language": LanguageAggregator()
}


# --------------------
# Helpers
# --------------------
async def call_service(service_cfg: dict, payload: dict):
    async with httpx.AsyncClient(timeout=service_cfg["timeout"]) as client:
        resp = await client.post(service_cfg["url"], json=payload)
        resp.raise_for_status()
        return resp.json()


def load_test_config(test_type: str):
    path = BASE_DIR / "tests" / f"{test_type}.yaml"
    if not path.exists():
        raise HTTPException(404, f"Unknown test type: {test_type}")

    with open(path) as f:
        return yaml.safe_load(f)


# --------------------
# API
# --------------------
@app.post("/score")
async def score(payload: ScoreRequest):
    """
    Expected payload:
    {
        "test_type": "summarize_written_text",
        "passage": "...",
        "summary": "..."
    }
    """

    payload = payload.dict()
    test_type = payload["test_type"]

    test_cfg = load_test_config(test_type)

    # --------------------
    # Call services in parallel (CORRECT WAY)
    # --------------------
    tasks = {}

    for svc_name in test_cfg["services"]:
        svc = SERVICES[svc_name]

        if svc_name == "content":
            svc_payload = {
                "passage": payload["passage"],
                "summary": payload["summary"]
            }
        else:  # language
            svc_payload = {
                "text": payload["summary"]
            }

        tasks[svc_name] = call_service(svc, svc_payload)

    results = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True
    )

    service_outputs = {}
    errors = {}

    for svc_name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            errors[svc_name] = str(result)
        else:
            service_outputs[svc_name] = result

    # --------------------
    # Aggregation
    # --------------------
    combined_output = {}

    for svc_name, output in service_outputs.items():
        rules = test_cfg["aggregation"][svc_name]
        aggregator = AGGREGATORS[svc_name]

        result = aggregator.aggregate(output, rules)
        combined_output[svc_name] = result

    return {
        "services": combined_output,
        "errors": errors if errors else None
    }
