from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import networkx as nx
# Assuming your optimizer class is saved in a file named aridaq.py, or paste it right above!
# from aridaq import ARIDAQOptimizer, ARIDAQConfig, ARIDAQError

app = FastAPI(title="CancerLock API 🧬")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OptimizationRequest(BaseModel):
    source_node: str
    target_node: str
    # You can pass nodes/edges or configure graph inputs here

@app.post("/api/optimize")
def run_cancer_optimization(data: OptimizationRequest):
    try:
        # Build a mock dynamic graph using your engine metrics (DepMap / Patient data simulation)
        G = nx.Graph()
        
        # Adding sample oncogenic states/transitions (e.g., TP53 mutation pathways)
        G.add_node("Node_A", energy_low=2.1, energy_high=5.4)
        G.add_node("Node_B", energy_low=1.5, energy_high=4.2)
        G.add_node("Node_C", energy_low=0.8, energy_high=2.9)
        
        G.add_edge("Node_A", "Node_B", distance_nm=1.2, charge_i=1.0, charge_j=-1.0, energy_low=2.0, energy_high=4.0, friction=0.2)
        G.add_edge("Node_B", "Node_C", distance_nm=0.9, charge_i=-1.0, charge_j=1.0, energy_low=1.0, energy_high=3.0, friction=0.1)

        optimizer = ARIDAQOptimizer()
        result = optimizer.optimize(G, data.source_node, data.target_node)
        
        return {
            "status": "success",
            "project": "CancerLock",
            "optimization_results": result,
            "clinical_note": "Route optimized for biomedical engineering target delivery."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str.error(e) if hasattr(e, 'error') else str(e))

@app.get("/")
def health_check():
    return {"status": "CancerLock API is online and optimizing 🚀"}

from typing import Any

import networkx as nx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.aridaq_optimizer import (
    ARIDAQConfig,
    ARIDAQError,
    ARIDAQOptimizer,
)

app = FastAPI(
    title="CancerLock API",
    description="Research API for cancer network optimization.",
    version="0.2.0",
)


class NodeInput(BaseModel):
    id: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class EdgeInput(BaseModel):
    source: str
    target: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class OptimizeRequest(BaseModel):
    nodes: list[NodeInput]
    edges: list[EdgeInput]
    source: str
    target: str
    directed: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class ExperimentRequest(BaseModel):
    experiment_data: dict[str, Any]
    question: str = (
        "Analyze these results, including biological "
        "meaning, limitations, and next steps."
    )


@app.get("/")
def home():
    return {
        "project": "CancerLock",
        "status": "running",
        "version": "0.2.0",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/optimize")
def optimize(request: OptimizeRequest):
    try:
        graph_type = nx.DiGraph if request.directed else nx.Graph
        graph = graph_type()

        for node in request.nodes:
            graph.add_node(node.id, **node.attributes)

        for edge in request.edges:
            if edge.source not in graph or edge.target not in graph:
                raise ARIDAQError(
                    "Every edge must reference existing nodes."
                )

            graph.add_edge(
                edge.source,
                edge.target,
                **edge.attributes,
            )

        config = ARIDAQConfig(**request.config)
        optimizer = ARIDAQOptimizer(config)

        result = optimizer.optimize(
            graph,
            request.source,
            request.target,
        )

        return {
            "project": "CancerLock",
            "engine": "ARIDAQ",
            "result": result,
            "interpretation": (
                "This is an energy-informed graph-search result, "
                "not a clinically validated treatment recommendation."
            ),
        }

    except ARIDAQError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/analyze")
def analyze(request: ExperimentRequest):
    try:
        from app.meta_model import explain_experiment

        result = explain_experiment(
            experiment_data=request.experiment_data,
            question=request.question,
        )

        return {
            "project": "CancerLock",
            "engine": "Meta Model API",
            "analysis": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Analysis request failed: {str(exc)}",
        )
import os
from openai import OpenAI

# Initialize the client pointing to Meta's Model API
# (It uses OpenAI-compatible routing under the hood)
meta_client = OpenAI(
    api_key=os.environ.get("MODEL_API_KEY"),
    base_url="https://api.meta.ai/v1"
)

@app.post("/api/ai-clinical-insights")
def get_meta_ai_insights(node_name: str, optimization_cost: float):
    try:
        # Prompting Meta's Muse model (e.g., Muse Wonder or Muse Spark) for doctor-ready notes
        response = meta_client.chat.completions.create(
            model="muse-spark-1.3",  # Or muse-wonder-1.0
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert oncology clinical assistant helping biomedical engineers interpret non-Euclidean graph optimization paths."
                },
                {
                    "role": "user", 
                    "content": f"Analyze target node {node_name} with an energy optimization cost of {optimization_cost}. Provide 3 critical clinical takeaways for a doctor."
                }
            ],
            max_tokens=300
        ]
        
        return {
            "status": "success",
            "ai_insights": response.choices[0].message.content
        }
    except Exception as e:
        return {"error": str(e)}
": f"Analyze target node {node_name} with an energy optimization cost of {optimization_cost}. Provide 3 critical clinical takeaways for a doctor."
                }
            ],
            max_tokens=300
        ]
        
        return {
            "status": "success",
            "ai_insights": response.choices[0].message.content
        }
    except Exception as e:
        return {"error": str(e)}

