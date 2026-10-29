"""
CancerLock: Biological Network Builder

Uses mutation-analysis results and STRING protein interaction data
to construct a biological network for subsequent ARIDAQ experiments.

This is exploratory research, not a clinical treatment predictor.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

INPUT_FILE = DATA_DIR / "mutation_summary.json"
NETWORK_FILE = DATA_DIR / "biological_network.json"
SUMMARY_FILE = DATA_DIR / "network_summary.json"

STRING_API = "https://string-db.org/api"
SPECIES_ID = 9606  # Homo sapiens
MINIMUM_SCORE = 700  # STRING confidence score threshold: 0–1000
MAX_GENES = 20


def load_mutated_genes():
    """Load the leading mutated genes from the previous experiment."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE.relative_to(ROOT)} does not exist. "
            "Run scripts/run_experiment.py successfully first."
        )

    with INPUT_FILE.open(encoding="utf-8") as file:
        summary = json.load(file)

    genes = [
        item["gene"]
        for item in summary.get("top_mutated_genes", [])
        if item.get("gene") and item["gene"] != "UNKNOWN"
    ]

    genes = list(dict.fromkeys(genes))[:MAX_GENES]

    if len(genes) < 2:
        raise ValueError(
            "At least two identified genes are needed to build "
            "an interaction network."
        )

    return genes, summary


def fetch_interactions(genes):
    """Retrieve STRING interactions for the selected human genes."""
    endpoint = f"{STRING_API}/json/network"

    parameters = {
        "identifiers": "\r".join(genes),
        "species": SPECIES_ID,
        "required_score": MINIMUM_SCORE,
        "caller_identity": "CancerLockHackathon",
    }

    with httpx.Client(
        timeout=60.0,
        follow_redirects=True,
    ) as client:
        response = client.get(endpoint, params=parameters)
        response.raise_for_status()
        records = response.json()

    if not isinstance(records, list):
        raise RuntimeError(
            "STRING returned an unexpected interaction response."
        )

    return records


def build_graph(genes, records):
    """Create normalized nodes and edges from interaction records."""
    nodes = {
        gene: {
            "id": gene,
            "source": "mutation_analysis",
        }
        for gene in genes
    }

    edges = {}
    unresolved_names = set()

    for record in records:
        gene_a = record.get("preferredName_A")
        gene_b = record.get("preferredName_B")
        score = record.get("score")

        if not gene_a or not gene_b or score is None:
            continue

        try:
            score = float(score)
        except (TypeError, ValueError):
            continue

        if gene_a == gene_b:
            continue

        # STRING may return interaction partners that were not among
        # the initially selected mutated genes. Keep them visible.
        for gene in (gene_a, gene_b):
            if gene not in nodes:
                nodes[gene] = {
                    "id": gene,
                    "source": "STRING_interaction_partner",
                }
                unresolved_names.add(gene)

        pair = tuple(sorted((gene_a, gene_b)))

        # Keep the highest score if a pair occurs more than once.
        if pair not in edges or score > edges[pair]["score"]:
            edges[pair] = {
                "source": pair[0],
                "target": pair[1],
                "score": score,
                "score_scale": "STRING 0–1000",
                "evidence_source": "STRING",
            }

    return (
        list(nodes.values()),
        list(edges.values()),
        sorted(unresolved_names),
    )


def analyze_network(nodes, edges, selected_genes):
    """Calculate structural properties without inventing biology."""
    degree = {node["id"]: 0 for node in nodes}
    selected_set = set(selected_genes)

    for edge in edges:
        source = edge["source"]
        target = edge["target"]

        degree[source] = degree.get(source, 0) + 1
        degree[target] = degree.get(target, 0) + 1

    ranked_nodes = sorted(
        (
            {
                "gene": gene,
                "degree": count,
                "selected_mutated_gene": gene in selected_set,
            }
            for gene, count in degree.items()
        ),
        key=lambda item: (-item["degree"], item["gene"]),
    )

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "selected_mutated_genes": selected_genes,
        "selected_gene_count": len(selected_genes),
        "isolated_nodes": [
            gene for gene, count in degree.items() if count == 0
        ],
        "degree_ranking": ranked_nodes,
        "interpretation_limitations": [
            (
                "STRING interactions may be functional associations "
                "and do not always represent direct physical binding."
            ),
            (
                "An interaction score is not a probability that "
                "a treatment will work."
            ),
            (
                "Network degree alone does not establish that a gene "
                "is a useful or safe treatment target."
            ),
            (
                "This network is based on selected mutated genes and "
                "their returned partners, not a complete cancer pathway."
            ),
        ],
    }


def main():
    print("=" * 60)
    print("CANCERLOCK | BIOLOGICAL NETWORK BUILDER")
    print("=" * 60)

    try:
        genes, mutation_summary = load_mutated_genes()

        print(f"Selected genes: {len(genes)}")
        print("Fetching human protein interaction data...")

        records = fetch_interactions(genes)

        nodes, edges, added_partners = build_graph(genes, records)

        network = {
            "metadata": {
                "project": "CancerLock",
                "created_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "organism": "Homo sapiens",
                "taxon_id": SPECIES_ID,
                "interaction_database": "STRING",
                "minimum_string_score": MINIMUM_SCORE,
                "mutation_study": mutation_summary.get("study_id"),
                "selected_gene_count": len(genes),
                "returned_interaction_records": len(records),
                "warning": (
                    "Exploratory biological network; not a "
                    "clinically validated treatment model."
                ),
            },
            "nodes": nodes,
            "edges": edges,
        }

        summary = analyze_network(nodes, edges, genes)

        summary["metadata"] = network["metadata"]
        summary["additional_interaction_partners"] = added_partners

        with NETWORK_FILE.open("w", encoding="utf-8") as file:
            json.dump(network, file, indent=2)

        with SUMMARY_FILE.open("w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2)

    except (
        httpx.HTTPError,
        FileNotFoundError,
        RuntimeError,
        ValueError,
        KeyError,
    ) as exc:
        print(f"\nNETWORK BUILD FAILED: {exc}", file=sys.stderr)
        print(
            "No successful network result is being reported. "
            "Check the input files and STRING API availability."
        )
        sys.exit(1)

    print("\nNETWORK BUILD COMPLETED")
    print(f"Network nodes: {summary['node_count']}")
    print(f"Network edges: {summary['edge_count']}")

    print("\nMOST CONNECTED GENES")
    for item in summary["degree_ranking"][:10]:
        print(f"  {item['gene']}: degree {item['degree']}")

    print("\nSAVED FILES")
    print(f"  {NETWORK_FILE.relative_to(ROOT)}")
    print(f"  {SUMMARY_FILE.relative_to(ROOT)}")

    print(
        "\nNEXT: validate network evidence, define the optimization "
        "objective, and integrate the verified ARIDAQ equations."
    )


if __name__ == "__main__":
    main()