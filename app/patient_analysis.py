from typing import Any

from pydantic import BaseModel, Field, field_validator


class MutationRecord(BaseModel):
    gene: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )

    variant: str | None = Field(
        default=None,
        max_length=100,
    )

    chromosome: str | None = None
    position: int | None = Field(default=None, gt=0)
    reference_allele: str | None = None
    alternate_allele: str | None = None
    classification: str | None = None


class PatientAnalysisInput(BaseModel):
    # Use a pseudonymous research ID, never a patient's name.
    case_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    cancer_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    mutations: list[MutationRecord] = Field(
        ...,
        min_length=1,
        max_length=1000,
    )

    gene_expression: dict[str, float] = Field(
        default_factory=dict,
    )

    laboratory_results: dict[str, Any] = Field(
        default_factory=dict,
    )

    objective: str = Field(
        default="analyze_connectivity",
        min_length=3,
        max_length=100,
    )

    @field_validator("case_id", "cancer_type")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be blank.")

        return value


def prepare_analysis(
    patient: PatientAnalysisInput,
) -> dict[str, Any]:
    """
    Validate and normalize submitted research data.

    This prepares data for downstream analysis. It does not
    independently identify drug targets or recommend treatment.
    """

    genes = sorted(
        {
            mutation.gene.strip().upper()
            for mutation in patient.mutations
        }
    )

    mutations = [
        mutation.model_dump(exclude_none=True)
        for mutation in patient.mutations
    ]

    return {
        "case_id": patient.case_id,
        "cancer_type": patient.cancer_type,
        "objective": patient.objective,
        "mutations": mutations,
        "mutated_genes": genes,
        "mutation_count": len(mutations),
        "unique_gene_count": len(genes),
        "gene_expression": patient.gene_expression,
        "laboratory_results": patient.laboratory_results,
        "status": "validated_for_research_pipeline",
        "limitations": [
            "Input validation is not clinical validation.",
            "Mutation annotations and biological evidence "
            "must be checked against trusted sources.",
            "No treatment recommendation is generated here.",
        ],
    }