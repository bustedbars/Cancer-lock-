"""
CancerLock: Interactive Biological Network Visualization

Reads the network built from mutation data and generates an
interactive HTML visualization using Plotly and NetworkX.

This visualizes network structure, not treatment effectiveness.
"""

import json
import sys
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

NETWORK_FILE = DATA_DIR / "biological_network.json"
OUTPUT_FILE = DATA_DIR / "network_visualization.html"


def load_network():
    if not NETWORK_FILE.exists():
        raise FileNotFoundError(
            "biological_network.json is missing. "
            "Run scripts/build_network.py successfully first."
        )

    with NETWORK_FILE.open(encoding="utf-8") as file:
        data = json.load(file)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not nodes:
        raise ValueError("The network contains no nodes.")

    return data, nodes, edges


def create_visualization(data, nodes, edges):
    graph = nx.Graph()

    for node in nodes:
        graph.add_node(
            node["id"],
            source=node.get("source", "unknown"),
        )

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")

        if source in graph and target in graph:
            graph.add_edge(
                source,
                target,
                score=float(edge.get("score", 0)),
            )

    # Seeded layout makes the same network easier to compare
    # across repeated runs.
    positions = nx.spring_layout(
        graph,
        seed=42,
        weight="score",
        iterations=100,
    )

    edge_x = []
    edge_y = []

    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]

        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1),
        hoverinfo="none",
        name="Interactions",
    )

    node_ids = list(graph.nodes())
    node_x = [positions[node][0] for node in node_ids]
    node_y = [positions[node][1] for node in node_ids]

    degrees = dict(graph.degree())

    node_sources = [
        graph.nodes[node].get("source", "unknown")
        for node in node_ids
    ]

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_ids,
        textposition="top center",
        customdata=[
            [
                degrees[node],
                node_sources[index],
            ]
            for index, node in enumerate(node_ids)
        ],
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Connections: %{customdata[0]}<br>"
            "Node source: %{customdata[1]}"
            "<extra></extra>"
        ),
        marker=dict(
            size=[
                12 + min(degrees[node] * 2, 24)
                for node in node_ids
            ],
            color=[degrees[node] for node in node_ids],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Connections"),
            line=dict(width=1),
        ),
        name="Genes",
    )

    metadata = data.get("metadata", {})

    figure = go.Figure(
        data=[edge_trace, node_trace]
    )

    figure.update_layout(
        title=(
            "CancerLock | Biological Interaction Network"
            f"<br><sup>{metadata.get('interaction_database', 'Unknown source')} "
            f"| {len(node_ids)} nodes | {graph.number_of_edges()} edges"
            "</sup>"
        ),
        template="plotly_dark",
        hovermode="closest",
        showlegend=False,
        margin=dict(l=20, r=20, t=90, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=(
                    "Exploratory network visualization. "
                    "Connectivity does not establish treatment effectiveness."
                ),
                xref="paper",
                yref="paper",
                x=0,
                y=-0.05,
                showarrow=False,
                align="left",
            )
        ],
    )

    return figure, graph


def main():
    print("=" * 60)
    print("CANCERLOCK | NETWORK VISUALIZATION")
    print("=" * 60)

    try:
        data, nodes, edges = load_network()
        figure, graph = create_visualization(data, nodes, edges)

        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        figure.write_html(
            str(OUTPUT_FILE),
            include_plotlyjs=True,
            full_html=True,
        )

    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print(
            f"VISUALIZATION FAILED: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("VISUALIZATION CREATED")
    print(f"Nodes: {graph.number_of_nodes()}")
    print(f"Edges: {graph.number_of_edges()}")
    print(f"Output: {OUTPUT_FILE.relative_to(ROOT)}")
    print(
        "Open the HTML file in a browser to explore "
        "the interactive network."
    )


if __name__ == "__main__":
    main()