import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.meta_model import explain_experiment, MetaModelError


app = FastAPI(
    title="CancerLock API",
    description=(
        "Computational cancer biology research using "
        "ARIDAQ and AI-assisted experiment explanations."
    ),
    version="0.1.0",
)


class ExperimentRequest(BaseModel):
    experiment_data: dict = Field(
        ...,
        description="Results from a CancerLock experiment.",
    )
    question: str = Field(
        default="Explain these results and their limitations.",
        min_length=3,
        max_length=1000,
    )


@app.get("/")
def root():
    return {
        "name": "CancerLock API",
        "status": "running",
        "version": "0.1.0",
        "endpoints": [
            "/health",
            "/explain",
            "/docs",
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "meta_api_key_configured": bool(
            os.getenv("MODEL_API_KEY")
        ),
    }


@app.post("/explain")
def explain(request: ExperimentRequest):
    """Explain supplied experiment results using Meta's model."""

    try:
        result = explain_experiment(
            experiment_data=request.experiment_data,
            question=request.question,
        )
        return result

    except MetaModelError as exc:
        message = str(exc)

        if "missing" in message.lower() or "not configured" in message.lower():
            raise HTTPException(
                status_code=503,
                detail="Meta API credentials are not configured.",
            )

        if "HTTP 401" in message or "HTTP 403" in message:
            raise HTTPException(
                status_code=502,
                detail="Meta API authentication failed or access was denied.",
            )

        if "HTTP 429" in message:
            raise HTTPException(
                status_code=503,
                detail="Meta API rate limit or usage limit reached.",
            )

        raise HTTPException(
            status_code=502,
            detail=message,
        )