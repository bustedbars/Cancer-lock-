
from __future__ import annotations

from collections import defaultdict
from typing import Any


class MutationAnalysisError(ValueError):
    """Raised when mutation data cannot be analyzed."""


# DepMap and common mutation annotation column names.
ALIASES = {
    "gene": ["Hugo_Symbol", "gene", "Gene", "gene_symbol"],
    "gene_id": ["Entrez_Gene_Id", "gene_id"],
    "classification": [
        "Variant_Classification",
        "variant_classification",
        "consequence",
    ],
    "variant_type": ["Variant_Type", "variant_type"],
    "protein_change": [
        "HGVSp_Short", "protein_change", "HGVSp"
    ],
    "coding_change": ["HGVSc", "coding_change"],
    "chromosome": ["Chromosome", "chromosome"],
    "start": ["Start_Position", "start_position"],
    "end": ["End_Position", "end_position"],
    "reference": ["Reference_Allele", "reference_allele"],
    "alternate": [
        "Tumor_Seq_Allele2",
        "Tumor_Allele",
        "alternate_allele",
    ],
    "model_id": ["DepMap_ID", "ModelID", "model_id"],
    "driver": ["is_driver", "driver_status", "driver_annotation"],
    "pathways": ["pathways", "Pathways", "pathway_annotations"],
    "evidence": ["evidence", "Evidence", "evidence_level"],
    "resistance": [
        "resistance_annotation",
        "Resistance_Annotation",
    ],
}


def get_value(record: dict, field: str) -> Any:
    """Retrieve a field using supported column aliases."""

    for column in ALIASES.get(field, []):
        value = record.get(column)

        if value is not None and str(value).strip():
            return value

    return None


def clean_value(value: Any) -> str | None:
    if value is None:
        return None

    result = str(value).strip()

    if not result or result.lower() in {
        "nan", "none", "null", "na"
    }:
        return None

    return result


def analyze_mutation_records(
    records: list[dict[str, Any]],
    model_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Analyze supplied mutation records.

    This module organizes mutation evidence. It does not
    independently establish pathogenicity, drug sensitivity,
    treatment suitability, or clinical diagnosis.

    DepMap cell-line data must not be represented as a
    patient's own tumor sequencing results.
    """

    if not isinstance(records, list) or not records:
        raise MutationAnalysisError(
            "Provide at least one mutation record."
        )

    if not all(isinstance(row, dict) for row in records):
        raise MutationAnalysisError(
            "Every mutation record must be a dictionary."
        )

    genes = defaultdict(list)
    classifications = defaultdict(int)
    pathways = defaultdict(set)
    driver_annotations = defaultdict(set)
    resistance_annotations = defaultdict(set)

    missing_gene_count = 0
    missing_classification_count = 0
    missing_protein_change_count = 0
    missing_evidence_count = 0

    normalized_records = []

    for index, record in enumerate(records):
        gene = clean_value(get_value(record, "gene"))
        classification = clean_value(
            get_value(record, "classification")
        )
        protein_change = clean_value(
            get_value(record, "protein_change")
        )

        if not gene:
            missing_gene_count += 1
            continue

        if not classification:
            missing_classification_count += 1

        if not protein_change:
            missing_protein_change_count += 1

        evidence = clean_value(get_value(record, "evidence"))

        if not evidence:
            missing_evidence_count += 1

        normalized = {
            "gene": gene,
            "gene_id": clean_value(
                get_value(record, "gene_id")
            ),
            "variant_classification": classification,
            "variant_type": clean_value(
                get_value(record, "variant_type")
            ),
            "protein_change": protein_change,
            "coding_change": clean_value(
                get_value(record, "coding_change")
            ),
            "chromosome": clean_value(
                get_value(record, "chromosome")
            ),
            "start_position": clean_value(
                get_value(record, "start")
            ),
            "end_position": clean_value(
                get_value(record, "end")
            ),
            "reference_allele": clean_value(
                get_value(record, "reference")
            ),
            "alternate_allele": clean_value(
                get_value(record, "alternate")
            ),
            "model_id": clean_value(
                get_value(record, "model_id")
            ),
            "driver_annotation": clean_value(
                get_value(record, "driver")
            ),
            "pathway_annotations": clean_value(
                get_value(record, "pathways")
            ),
            "evidence_annotation": evidence,
            "resistance_annotation": clean_value(
                get_value(record, "resistance")
            ),
        }

        genes[gene].append(normalized)
        normalized_records.append(normalized)

        if classification:
            classifications[classification] += 1

        if normalized["pathway_annotations"]:
            for pathway in normalized["pathway_annotations"].split(";"):
                pathways[gene].add(pathway.strip())

        if normalized["driver_annotation"]:
            driver_annotations[gene].add(
                normalized["driver_annotation"]
            )

        if normalized["resistance_annotation"]:
            resistance_annotations[gene].add(
                normalized["resistance_annotation"]
            )

    if not normalized_records:
        raise MutationAnalysisError(
            "No usable records contained a recognized gene symbol."
        )

    gene_summary = []

    for gene, mutations in sorted(genes.items()):
        gene_summary.append({
            "gene": gene,
            "mutation_count": len(mutations),
            "variant_classifications": sorted({
                item["variant_classification"]
                for item in mutations
                if item["variant_classification"]
            }),
            "protein_changes": sorted({
                item["protein_change"]
                for item in mutations
                if item["protein_change"]
            }),
            "pathway_annotations": sorted(pathways[gene]),
            "driver_annotations": sorted(
                driver_annotations[gene]
            ),
            "resistance_annotations": sorted(
                resistance_annotations[gene]
            ),
            "mutations": mutations,
        })

    models = sorted({
        item["model_id"]
        for item in normalized_records
        if item["model_id"]
    })

    metadata = model_metadata or {}

    return {
        "project": "CancerLock",
        "analysis_type": "Acquired mutation evidence analysis",
        "data_source": metadata.get(
            "data_source", "Not specified"
        ),
        "model_context": metadata.get(
            "model_context",
            "Unverified. Confirm whether data represents "
            "a cell line, organoid, or patient tumor."
        ),
        "sample_or_model_id": models,
        "summary": {
            "input_records": len(records),
            "usable_mutation_records": len(normalized_records),
            "unique_affected_genes": len(genes),
            "variant_classification_counts": dict(
                classifications
            ),
        },
        "gene_analysis": gene_summary,
        "data_quality": {
            "records_missing_gene": missing_gene_count,
            "records_missing_classification": (
                missing_classification_count
            ),
            "records_missing_protein_change": (
                missing_protein_change_count
            ),
            "records_missing_evidence_annotation": (
                missing_evidence_count
            ),
            "pathway_annotations_available": any(pathways.values()),
            "driver_annotations_available": any(
                driver_annotations.values()
            ),
            "resistance_annotations_available": any(
                resistance_annotations.values()
            ),
        },
        "research_interpretation": {
            "candidate_vulnerabilities": [],
            "potential_resistance_mechanisms": [],
            "pathway_dependencies": [],
            "status": "Requires additional biological evidence.",
            "next_step": (
                "Integrate pathway, gene dependency, expression, "
                "copy-number and functional evidence before "
                "ranking research hypotheses."
            ),
        },
        "limitations": [
            "Mutation presence alone does not establish that "
            "a mutation drives cancer.",
            "A mutation does not independently establish "
            "drug sensitivity or resistance.",
            "Missing annotations are not evidence of absence.",
            "DepMap cell-line findings are not automatically "
            "patient-specific findings.",
            "This output is research support, not a clinical "
            "diagnosis or treatment recommendation."
        ],
    }
