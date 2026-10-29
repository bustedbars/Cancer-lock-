import os
import httpx


API_URL = "https://api.meta.ai/v1/chat/completions"
DEFAULT_MODEL = "muse-spark-1.3"


class MetaModelError(Exception):
    """Raised when the Meta Model API request fails."""
    pass


def explain_experiment(
    experiment_data: dict,
    question: str = (
        "Explain these CancerLock experiment results, "
        "including limitations and possible next steps."
    ),
) -> str:
    """
    Ask Meta's model to interpret experiment data.
    This function does not run the ARIDAQ algorithm.
    """

    api_key = os.getenv("MODEL_API_KEY")
    model = os.getenv("MODEL_NAME", DEFAULT_MODEL)

    if not api_key:
        raise MetaModelError(
            "MODEL_API_KEY is not configured."
        )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the scientific explanation component "
                    "of CancerLock, an exploratory computational "
                    "cancer-biology research prototype. "
                    "Explain supplied results accurately. "
                    "Never invent data, claim an experiment ran "
                    "when it did not, or present predictions as "
                    "proven treatments. Clearly state limitations."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Experiment data:\n{experiment_data}\n\n"
                    f"Question:\n{question}"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.is_error:
            raise MetaModelError(
                f"Meta API returned HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        result = response.json()
        answer = result["choices"][0]["message"]["content"]

        if not answer:
            raise MetaModelError(
                "The Meta API returned an empty response."
            )

        return answer.strip()

    except httpx.RequestError as exc:
        raise MetaModelError(
            f"Could not connect to Meta API: {exc}"
        ) from exc

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MetaModelError(
            "The Meta API returned an unexpected response."
        ) from exc