"""
CancerLock: Network Robustness and Optimization Baseline

Evaluates hypothetical node disruptions in a biological interaction
network using sparse graph representations.

This is a structural experiment, NOT the ARIDAQ algorithm and NOT
a clinical treatment recommendation.

The verified ARIDAQ equations must be integrated separately.
"""

import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

INPUT_FILE = DATA_DIR / "biological_network.json"
OUTPUT_FILE = DATA_DIR / "robustness_analysis.json"

# Limit exhaustive node-disruption testing in the first experiment.
MAX_CANDIDATES = 100


def load_network():
    """Load and validate the previously constructed network."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "biological_network.json is missing. "
            "Run the data and network-building scripts first."
        )

    with INPUT_FILE.open(encoding="utf-8") as file:
        data = json.load(file)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    node_ids = [node.get("id") for node in nodes]

    if not node_ids or any(not node for node in node_ids):
        raise ValueError("Network nodes must have valid identifiers.")

    if len(set(node_ids)) != len(node_ids):
        raise ValueError("Duplicate node identifiers were found.")

    known_nodes = set(node_ids)

    for edge in edges:
        if (
            edge.get("source") not in known_nodes
            or edge.get("target") not in known_nodes
        ):
            raise ValueError(
                "An edge references a node that is not in the network."
            )

    return data, node_ids, edges


def create_sparse_adjacency(node_ids, edges):
    """Create a sparse undirected adjacency matrix."""
    index = {
        node_id: position
        for position, node_id in enumerate(node_ids)
    }

    rows = []
    columns = []
    values = []

    for edge in edges:
        source = index[edge["source"]]
        target = index[edge["target"]]

        if source == target:
            continue

        rows.extend([source, target])
        columns.extend([target, source])

        # STRING scores are confidence scores, not physical energies.
        # Use an unweighted adjacency matrix for this baseline.
        values.extend([1.0, 1.0])

    adjacency = csr_matrix(
        (values, (rows, columns)),
        shape=(len(node_ids), len(node_ids)),
        dtype=np.float64,
    )

    adjacency.data[:] = 1.0
    adjacency.eliminate_zeros()

    return adjacency


def largest_component_size(adjacency):
    """Return the largest connected-component size."""
    if adjacency.shape[0] == 0:
        return 0

    component_count, labels = connected_components(
        adjacency,
        directed=False,
        return_labels=True,
    )

    if component_count == 0:
        return 0

    sizes = np.bincount(labels)

    return int(sizes.max()) if len(sizes) else 0


def evaluate_node_disruptions(node_ids, adjacency):
    """
    Measure structural effects of hypothetically removing each node.

    A higher score means a greater reduction in the largest connected
    component. It does not mean the node is a valid medical target.
    """
    baseline_size = largest_component_size(adjacency)
    results = []

    candidate_count = min(len(node_ids), MAX_CANDIDATES)

    for candidate_index in range(candidate_count):
        keep = np.ones(len(node_ids), dtype=bool)
        keep[candidate_index] = False

        reduced = adjacency[keep][:, keep]
        remaining_largest = largest_component_size(reduced)

        disruption = baseline_size - remaining_largest

        results.append(
            {
                "node": node_ids[candidate_index],
                "baseline_largest_component": baseline_size,
                "largest_component_after_removal": remaining_largest,
                "nodes_removed_from_largest_component": disruption,
                "relative_structural_change": (
                    float(disruption / baseline_size)
                    if baseline_size
                    else 0.0
                ),
                "interpretation": (
                    "Hypothetical graph disruption only; "
                    "not a treatment recommendation."
                ),
            }
        )

    results.sort(
        key=lambda item: (
            -item["nodes_removed_from_largest_component"],
            item["node"],
        )
    )

    return baseline_size, results


def main():
    print("=" * 60)
    print("CANCERLOCK | NETWORK ROBUSTNESS EXPERIMENT")
    print("=" * 60)

    try:
        network_data, node_ids, edges = load_network()

        adjacency = create_sparse_adjacency(node_ids, edges)

        baseline_size, results = evaluate_node_disruptions(
            node_ids,
            adjacency,
        )

        output = {
            "metadata": {
                "project": "CancerLock",
                "experiment": "single_node_structural_disruption",
                "network_node_count": len(node_ids),
                "network_edge_count": len(edges),
                "baseline_largest_component_size": baseline_size,
                "candidate_count_evaluated": len(results),
                "computation": (
                    "NumPy and SciPy sparse graph calculations"
                ),
                "upstream_metadata": network_data.get("metadata", {}),
                "is_aridaq": False,
                "clinical_validation": False,
            },
            "ranked_hypothetical_disruptions": results,
            "limitations": [
                (
                    "This experiment removes graph nodes mathematically; "
                    "it does not model a drug or biological intervention."
                ),
                (
                    "STRING interactions do not encode all activating, "
                    "inhibiting, or context-specific biological effects."
                ),
                (
                    "Structural importance does not establish cancer "
                    "dependency, safety, or treatment effectiveness."
                ),
                (
                    "The ranking is not an ARIDAQ result."
                ),
            ],
        }

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with OUTPUT_FILE.open("w", encoding="utf-8") as file:
            json.dump(output, file, indent=2)

    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print(f"EXPERIMENT FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    print("EXPERIMENT COMPLETED")
    print(f"Nodes analyzed: {len(node_ids)}")
    print(f"Edges: {len(edges)}")
    print(f"Baseline largest component: {baseline_size}")

    print("\nTOP STRUCTURAL DISRUPTIONS")
    for result in results[:10]:
        print(
            f"  {result['node']}: "
            f"largest component "
            f"{result['largest_component_after_removal']} "
            f"(from {baseline_size})"
        )

    print(f"\nResults saved to: {OUTPUT_FILE.relative_to(ROOT)}")
    print(
        "\nThis is a structural baseline. The next stage is to "
        "integrate and validate the actual ARIDAQ mathematics."
    )


if __name__ == "__main__":
    main()