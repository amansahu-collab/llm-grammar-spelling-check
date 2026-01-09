from fastapi import FastAPI
from pydantic import BaseModel
from core import evaluate_text

app = FastAPI(title="Grammar & Spelling Evaluator")

class EvalRequest(BaseModel):
    text: str

@app.post("/evaluate")
def evaluate(payload: EvalRequest):
    return evaluate_text(payload.text)
