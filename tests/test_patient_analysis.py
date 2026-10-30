import pytest
from pydantic import ValidationError

from app.patient_analysis import (
    PatientAnalysisInput,
    prepare_analysis,
)


def test_valid_mutation_input():
    patient = PatientAnalysisInput(
        case_id="RESEARCH-001",
        cancer_type="breast cancer",
        mutations=[
            {
                "gene": "BRCA1",
                "variant": "example_variant",
            },
            {
                "gene": "TP53",
                "variant": "example_variant_2",
            },
        ],
    )

    result = prepare_analysis(patient)

    assert result["status"] == "validated_for_research_pipeline"
    assert result["mutation_count"] == 2
    assert result["unique_gene_count"] == 2
    assert result["mutated_genes"] == ["BRCA1", "TP53"]


def test_gene_names_are_normalized():
    patient = PatientAnalysisInput(
        case_id="RESEARCH-002",
        cancer_type="research case",
        mutations=[
            {"gene": "brca1"},
            {"gene": "TP53"},
        ],
    )

    result = prepare_analysis(patient)

    assert "BRCA1" in result["mutated_genes"]
    assert "TP53" in result["mutated_genes"]


def test_missing_mutations_are_rejected():
    with pytest.raises(ValidationError):
        PatientAnalysisInput(
            case_id="RESEARCH-003",
            cancer_type="research case",
            mutations=[],
        )


def test_blank_case_id_is_rejected():
    with pytest.raises(ValidationError):
        PatientAnalysisInput(
            case_id=" ",
            cancer_type="research case",
            mutations=[
                {"gene": "TP53"},
            ],
        )


def test_laboratory_results_are_preserved():
    patient = PatientAnalysisInput(
        case_id="RESEARCH-004",
        cancer_type="research case",
        mutations=[
            {"gene": "TP53"},
        ],
        laboratory_results={
            "example_measurement": 12.5,
        },
    )

    result = prepare_analysis(patient)

    assert (
        result["laboratory_results"]["example_measurement"]
        == 12.5
    )