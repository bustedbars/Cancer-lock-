from typing import Any


def build_research_report(
    analysis: dict[str, Any],
    network_results: dict[str, Any] | None = None,
    aridaq_results: dict[str, Any] | None = None,
    pathway_results: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Assemble a structured CancerLock research report.

    This function reports supplied results. It does not invent
    biological evidence, validate drug efficacy, or diagnose cancer.
    """

    network_results = network_results or {}
    aridaq_results = aridaq_results or {}
    pathway_results = pathway_results or []
    evidence = evidence or []

    mutations = analysis.get("mutations", [])
    genes = analysis.get("mutated_genes", [])

    limitations = list(analysis.get("limitations", []))

    sections = {
        "mutation_profile": {
            "cancer_type": analysis.get("cancer_type"),
            "mutation_count": len(mutations),
            "affected_genes": genes,
            "mutations": mutations,
            "gene_expression": analysis.get(
                "gene_expression", {}
            ),
            "laboratory_results": analysis.get(
                "laboratory_results", {}
            ),
        },

        "biological_pathways": {
            "results": pathway_results,
            "evidence_available": bool(pathway_results),
            "interpretation": (
                "Pathway results require review of their "
                "sources, statistical significance, and relevance."
                if pathway_results
                else "No pathway enrichment results were supplied."
            ),
        },

        "network_analysis": {
            "results": network_results,
            "evidence_available": bool(network_results),
            "interpretation": (
                "Network associations identify relationships "
                "for further investigation; they do not establish "
                "causation or therapeutic effectiveness."
            ),
        },

        "aridaq_optimization": {
            "results": aridaq_results,
            "optimization_available": bool(aridaq_results),
            "interpretation": (
                "Interpret routes using the implemented objective, "
                "energy terms, parameters, and search limitations."
                if aridaq_results
                else "ARIDAQ optimization results are not yet available."
            ),
        },

        "intervention_hypotheses": {
            "candidates": [],
            "status": "pending_evidence_review",
            "message": (
                "Candidate interventions must be derived from "
                "specific, traceable biological evidence and "
                "validated research. No treatment is recommended."
            ),
        },

        "alternative_routes": {
            "results": aridaq_results.get(
                "alternative_routes", []
            ),
            "status": (
                "available"
                if aridaq_results.get("alternative_routes")
                else "not_evaluated"
            ),
        },

        "resistance_analysis": {
            "results": aridaq_results.get(
                "resistance_analysis"
            ),
            "status": (
                "available"
                if aridaq_results.get("resistance_analysis")
                else "not_evaluated"
            ),
            "message": (
                "Resistance requires dedicated biological "
                "evidence and analysis; network connectivity "
                "alone cannot establish resistance."
            ),
        },

        "evidence_quality": {
            "sources": evidence,
            "source_count": len(evidence),
            "requires_review": True,
            "checks": [
                "Source provenance",
                "Evidence quality",
                "Statistical significance where applicable",
                "Data completeness",
                "Independent validation",
            ],
        },
    }

    if not network_results:
        limitations.append(
            "No network-analysis results were provided."
        )

    if not aridaq_results:
        limitations.append(
            "No ARIDAQ optimization results were provided."
        )

    if not pathway_results:
        limitations.append(
            "No pathway enrichment results were provided."
        )

    return {
        "report_type": "CancerLock computational research report",
        "case_id": analysis.get("case_id"),
        "status": "research_report_generated",
        "sections": sections,
        "limitations": list(dict.fromkeys(limitations)),
        "clinical_status": (
            "Research use only. Not a diagnosis or a validated "
            "treatment recommendation."
        ),
    }