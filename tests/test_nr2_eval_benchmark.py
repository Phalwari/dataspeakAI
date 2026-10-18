"""
DataSpeakAI — NR-2.2 AI Evaluation Benchmark Runner (Task NR-2.2-A-T07 & T08)

Executes the 25-case versioned evaluation set (eval_dataset_v1.json) offline:
- Evaluates SQL, RAG, and Hybrid factual answers (TC-01 to TC-11)
- Tests abstention on unanswerable queries (TC-12 to TC-14)
- Verifies deterministic detection and rejection of numerical hallucinations (TC-15 to TC-17)
- Verifies detection of conflicting dates and negation polarity conflicts (TC-18 to TC-21)
- Verifies prompt injection sanitization inside <document_evidence> tags (TC-22 to TC-24)
- Verifies honest unverified status on embedding outages (TC-25)
- Asserts 25/25 comprehensive pass rate across all benchmark dimensions
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.citation_service import CitationService, verify_numerical_and_negation
from routers.chat import sanitize_evidence_text
from routers.documents import _load_hf_embeddings


@pytest.fixture(scope="module")
def eval_dataset():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "nr2", "eval_dataset_v1.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def hf_embeddings():
    return _load_hf_embeddings("all-MiniLM-L6-v2")


def test_eval_dataset_structure_and_completeness(eval_dataset):
    """Verifies that the benchmark dataset contains the required version and 25 test cases."""
    assert eval_dataset["version"] == "1.0.0"
    assert len(eval_dataset["cases"]) == 25
    case_types = {c["type"] for c in eval_dataset["cases"]}
    expected_types = {
        "sql_supported", "rag_supported", "hybrid_supported",
        "unanswerable", "numerical_hallucination", "date_conflict",
        "negation_trap", "prompt_injection", "outage_simulation"
    }
    assert expected_types.issubset(case_types)


def test_eval_benchmark_sql_supported_grounding(eval_dataset, hf_embeddings):
    """
    Evaluates Cases TC-01 to TC-04 (SQL Supported):
    Verifies that SQL query aggregation/filter answers are grounded against executed result context,
    achieving supported status and meeting minimum confidence thresholds.
    """
    service = CitationService()
    sql_cases = [c for c in eval_dataset["cases"] if c["type"] == "sql_supported"]
    assert len(sql_cases) == 4

    for tc in sql_cases:
        ans = tc["ground_truth_answer"]
        ctx = tc["context_evidence"]
        res = service.verify_grounding(
            response_text=ans,
            retrieved_chunks=[{"content": ctx, "score": 0.85, "metadata": {"source": "sql_query.sql"}}],
            embedding_model=hf_embeddings
        )
        assert res["grounding_status"] == tc["expected_grounding_status"], (
            f"{tc['id']} failed: expected {tc['expected_grounding_status']}, got {res['grounding_status']}"
        )
        assert res["verified_claims_count"] >= 1, f"{tc['id']} has no verified claims"
        assert res["grounding_confidence"] >= tc["expected_min_confidence"], (
            f"{tc['id']} confidence {res['grounding_confidence']} below expected {tc['expected_min_confidence']}"
        )


def test_eval_benchmark_rag_supported_grounding(eval_dataset, hf_embeddings):
    """
    Evaluates Cases TC-05 to TC-09 (RAG Supported):
    Verifies that knowledge base document answers (including tables) are grounded against source passages.
    """
    service = CitationService()
    rag_cases = [c for c in eval_dataset["cases"] if c["type"] == "rag_supported"]
    assert len(rag_cases) == 5

    for tc in rag_cases:
        ans = tc["ground_truth_answer"]
        ctx = tc["context_evidence"]
        res = service.verify_grounding(
            response_text=ans,
            retrieved_chunks=[{"content": ctx, "score": 0.85, "metadata": {"source": "policy.pdf"}}],
            embedding_model=hf_embeddings
        )
        assert res["grounding_status"] == tc["expected_grounding_status"], (
            f"{tc['id']} failed: expected {tc['expected_grounding_status']}, got {res['grounding_status']}"
        )
        assert res["verified_claims_count"] >= 1, f"{tc['id']} has no verified claims"
        assert res["grounding_confidence"] >= tc["expected_min_confidence"], (
            f"{tc['id']} confidence {res['grounding_confidence']} below expected {tc['expected_min_confidence']}"
        )


def test_eval_benchmark_hybrid_supported_grounding(eval_dataset, hf_embeddings):
    """
    Evaluates Cases TC-10 & TC-11 (Hybrid Supported):
    Verifies that multi-source synthesized answers are grounded against combined SQL and document context.
    """
    service = CitationService()
    hybrid_cases = [c for c in eval_dataset["cases"] if c["type"] == "hybrid_supported"]
    assert len(hybrid_cases) == 2

    for tc in hybrid_cases:
        ans = tc["ground_truth_answer"]
        ctx = tc["context_evidence"]
        res = service.verify_grounding(
            response_text=ans,
            retrieved_chunks=[{"content": ctx, "score": 0.85, "metadata": {"source": "hybrid_source.txt"}}],
            embedding_model=hf_embeddings
        )
        assert res["grounding_status"] == tc["expected_grounding_status"], (
            f"{tc['id']} failed: expected {tc['expected_grounding_status']}, got {res['grounding_status']}"
        )
        assert res["verified_claims_count"] >= 1, f"{tc['id']} has no verified claims"
        assert res["grounding_confidence"] >= tc["expected_min_confidence"], (
            f"{tc['id']} confidence {res['grounding_confidence']} below expected {tc['expected_min_confidence']}"
        )


def test_eval_benchmark_unanswerable_abstention(eval_dataset, hf_embeddings):
    """
    Evaluates Cases TC-12 to TC-14 (Abstention on Missing Data):
    Verifies that unanswerable queries produce honest disclaimers with no factual claims,
    returning grounding_status='no_claims' and 0.0 confidence.
    """
    service = CitationService()
    unans_cases = [c for c in eval_dataset["cases"] if c["type"] == "unanswerable"]
    assert len(unans_cases) == 3

    for tc in unans_cases:
        ans = tc["ground_truth_answer"]
        ctx = tc["context_evidence"]
        res = service.verify_grounding(
            response_text=ans,
            retrieved_chunks=[{"content": ctx, "score": 0.5, "metadata": {"source": "empty.txt"}}],
            embedding_model=hf_embeddings
        )
        assert res["grounding_status"] == "no_claims", (
            f"{tc['id']} failed: expected no_claims, got {res['grounding_status']}"
        )
        assert res["total_claims_count"] == 0
        assert res["verified_claims_count"] == 0
        assert res["grounding_confidence"] == 0.0


def test_eval_benchmark_numerical_hallucinations_rejected(eval_dataset):
    """
    Evaluates Cases TC-15 to TC-17:
    Verifies that claims with modified/inflated numbers or percentages are caught
    by deterministic checks and never marked as supported.
    """
    service = CitationService()
    num_cases = [c for c in eval_dataset["cases"] if c["type"] == "numerical_hallucination"]
    assert len(num_cases) >= 3

    for tc in num_cases:
        claim = tc["hallucinated_claim"]
        chunk = tc["context_evidence"]
        valid, reason = verify_numerical_and_negation(claim, chunk)
        assert not valid, f"Failed to detect numerical trap in {tc['id']}: {tc['trap_description']}"
        assert "Numerical/date token mismatch" in reason

        # Verify through full CitationService pipeline
        mock_emb = MagicMock()
        mock_emb.embed_documents.return_value = [[1.0, 0.0, 0.0]]  # Mock high cosine match
        res = service.verify_grounding(
            response_text=claim,
            retrieved_chunks=[{"content": chunk, "score": 0.85, "metadata": {"source": "test.txt"}}],
            embedding_model=mock_emb
        )
        assert res["grounding_status"] == "unsupported", f"Expected unsupported for {tc['id']}, got {res['grounding_status']}"
        assert res["verified_claims_count"] == 0
        assert res["claim_coverage_ratio"] == 0.0


def test_eval_benchmark_date_conflicts_rejected(eval_dataset):
    """
    Evaluates Cases TC-18 & TC-19:
    Verifies that claims with conflicting years or dates are caught.
    """
    date_cases = [c for c in eval_dataset["cases"] if c["type"] == "date_conflict"]
    assert len(date_cases) >= 2

    for tc in date_cases:
        claim = tc["hallucinated_claim"]
        chunk = tc["context_evidence"]
        valid, reason = verify_numerical_and_negation(claim, chunk)
        assert not valid, f"Failed to detect date conflict in {tc['id']}: {tc['trap_description']}"
        assert "Numerical/date token mismatch" in reason


def test_eval_benchmark_negation_polarity_traps_rejected(eval_dataset):
    """
    Evaluates Cases TC-20 & TC-21:
    Verifies that claims where negation is inverted ('not' removed or added)
    are flagged as polarity mismatches and rejected.
    """
    neg_cases = [c for c in eval_dataset["cases"] if c["type"] == "negation_trap"]
    assert len(neg_cases) >= 2

    for tc in neg_cases:
        claim = tc["hallucinated_claim"]
        chunk = tc["context_evidence"]
        valid, reason = verify_numerical_and_negation(claim, chunk)
        assert not valid, f"Failed to detect negation inversion in {tc['id']}: {tc['trap_description']}"
        assert "Negation polarity mismatch" in reason


def test_eval_benchmark_prompt_injections_defused(eval_dataset):
    """
    Evaluates Cases TC-22 to TC-24:
    Verifies that prompt injection attempts within retrieved chunks are neutralized
    by sanitize_evidence_text before injection into prompts.
    """
    injection_cases = [c for c in eval_dataset["cases"] if c["type"] == "prompt_injection"]
    assert len(injection_cases) >= 3

    for tc in injection_cases:
        malicious = tc["malicious_chunk"]
        sanitized = sanitize_evidence_text(malicious)
        assert "Ignore all previous instructions" not in sanitized
        assert "Disregard prior instructions" not in sanitized
        assert "</document_evidence>" not in sanitized
        assert "<system>" not in sanitized
        assert tc["expected_defused_token"] in sanitized


def test_eval_benchmark_outage_simulation_honest_unverified(eval_dataset):
    """
    Evaluates Case TC-25:
    Simulates embedding cluster failure during grounding check.
    Verifies that status is 'unverified', confidence is 0.0, and has_low_confidence is True.
    """
    service = CitationService()
    faulty_embedder = MagicMock()
    faulty_embedder.embed_documents.side_effect = RuntimeError("Synthetic embedding cluster failure")

    tc = [c for c in eval_dataset["cases"] if c["type"] == "outage_simulation"][0]
    res = service.verify_grounding(
        response_text=tc["ground_truth_answer"],
        retrieved_chunks=[{"content": tc["context_evidence"], "score": 0.8, "metadata": {"source": "audit.txt"}}],
        embedding_model=faulty_embedder
    )

    assert res["grounding_status"] == "unverified"
    assert res["grounding_confidence"] == 0.0
    assert res["has_low_confidence"] is True
    assert res["claim_coverage_ratio"] == 0.0
    assert "Synthetic embedding cluster failure" in res["unverified_reason"]


def test_eval_benchmark_all_25_cases_comprehensive_pass_rate(eval_dataset, hf_embeddings):
    """
    Comprehensive aggregator test:
    Executes and asserts all 25 cases from eval_dataset_v1.json,
    confirming a 100% pass rate (25/25) across all benchmark dimensions.
    """
    service = CitationService()
    passed_cases = []
    failed_cases = []

    for tc in eval_dataset["cases"]:
        tc_id = tc["id"]
        tc_type = tc["type"]

        try:
            if tc_type in ("sql_supported", "rag_supported", "hybrid_supported"):
                res = service.verify_grounding(
                    response_text=tc["ground_truth_answer"],
                    retrieved_chunks=[{"content": tc["context_evidence"], "score": 0.85, "metadata": {"source": "doc.txt"}}],
                    embedding_model=hf_embeddings
                )
                assert res["grounding_status"] == tc["expected_grounding_status"]
                assert res["grounding_confidence"] >= tc["expected_min_confidence"]
                assert res["verified_claims_count"] >= 1
                passed_cases.append(tc_id)

            elif tc_type == "unanswerable":
                res = service.verify_grounding(
                    response_text=tc["ground_truth_answer"],
                    retrieved_chunks=[{"content": tc["context_evidence"], "score": 0.5, "metadata": {"source": "doc.txt"}}],
                    embedding_model=hf_embeddings
                )
                assert res["grounding_status"] == "no_claims"
                assert res["verified_claims_count"] == 0
                passed_cases.append(tc_id)

            elif tc_type in ("numerical_hallucination", "date_conflict"):
                valid, reason = verify_numerical_and_negation(tc["hallucinated_claim"], tc["context_evidence"])
                assert not valid
                assert "Numerical/date token mismatch" in reason
                passed_cases.append(tc_id)

            elif tc_type == "negation_trap":
                valid, reason = verify_numerical_and_negation(tc["hallucinated_claim"], tc["context_evidence"])
                assert not valid
                assert "Negation polarity mismatch" in reason
                passed_cases.append(tc_id)

            elif tc_type == "prompt_injection":
                sanitized = sanitize_evidence_text(tc["malicious_chunk"])
                assert "Ignore all previous instructions" not in sanitized
                assert tc["expected_defused_token"] in sanitized
                passed_cases.append(tc_id)

            elif tc_type == "outage_simulation":
                faulty = MagicMock()
                faulty.embed_documents.side_effect = RuntimeError("Synthetic outage")
                res = service.verify_grounding(
                    response_text=tc["ground_truth_answer"],
                    retrieved_chunks=[{"content": tc["context_evidence"], "score": 0.8, "metadata": {"source": "doc.txt"}}],
                    embedding_model=faulty
                )
                assert res["grounding_status"] == "unverified"
                assert res["has_low_confidence"] is True
                passed_cases.append(tc_id)

        except Exception as exc:
            failed_cases.append((tc_id, tc_type, str(exc)))

    assert len(failed_cases) == 0, f"Benchmark failures detected: {failed_cases}"
    assert len(passed_cases) == 25, f"Expected 25 passed cases, got {len(passed_cases)}"
