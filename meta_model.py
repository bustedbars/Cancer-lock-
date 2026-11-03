
import os
import json
import httpx


API_URL = "https://api.meta.ai/v1/chat/completions"
DEFAULT_MODEL = "muse-spark-1.3"


class MetaModelError(Exception):
    """Raised when the Meta Model API request fails."""
    pass


SYSTEM_INSTRUCTIONS = """
You are the biological reasoning and research intelligence
component of CancerLock.

Your responsibilities:
1. Interpret supplied cancer biology research data.
2. Identify relevant survival pathways and biological relationships.
3. Investigate potential resistance mechanisms.
4. Explain optimization results produced by Aridaq.
5. Identify uncertainties and missing evidence.
6. Suggest scientifically testable follow-up experiments.

Rules:
- Never invent biological data or gene interactions.
- Never claim a simulation or experiment was performed if it was not.
- Distinguish established evidence from hypotheses.
- Never present computational predictions as proven treatments.
- Consider healthy-cell selectivity and potential resistance.
- Clearly communicate scientific limitations.
"""


def explain_experiment(
    experiment_data: dict,
    question: str = (
        "Analyze these CancerLock research results. "
        "Explain biological significance, resistance risks, "
        "healthy-cell considerations, limitations and next steps."
    ),
) -> str:

    api_key = os.getenv("MODEL_API_KEY")
    model = os.getenv("MODEL_NAME", DEFAULT_MODEL)

    if not api_key:
        raise MetaModelError(
            "MODEL_API_KEY is not configured."
        )

    if not isinstance(experiment_data, dict):
        raise MetaModelError(
            "Experiment data must be a dictionary."
        )

    try:
        serialized_data = json.dumps(
            experiment_data,
            indent=2,
            allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise MetaModelError(
            "Experiment data must contain valid JSON-compatible values."
        ) from exc

    payload = {
        "model": model,
        "messages": [
            {
                "role": "developer",
                "content": SYSTEM_INSTRUCTIONS
            },
            {
                "role": "user",
                "content": (
                    f"EXPERIMENT DATA:\n{serialized_data}\n\n"
                    f"RESEARCH QUESTION:\n{question}"
                )
            }
        ],
        "max_completion_tokens": 1500
    }

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )

            response.raise_for_status()

        result = response.json()

        answer = result["choices"][0]["message"]["content"]

        if not isinstance(answer, str) or not answer.strip():
            raise MetaModelError(
                "Meta returned an empty or invalid response."
            )

        return answer.strip()

    except httpx.HTTPStatusError as exc:
        raise MetaModelError(
            f"Meta API error {exc.response.status_code}: "
            f"{exc.response.text[:500]}"
        ) from exc

    except httpx.RequestError as exc:
        raise MetaModelError(
            f"Meta connection failed: {exc}"
        ) from exc

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MetaModelError(
            "Meta returned an unexpected response format."
        ) from exc
