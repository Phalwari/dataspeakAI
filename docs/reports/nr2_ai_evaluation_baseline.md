> **Evidence correction — 2026-10-19:** The original 25 cases below test citation verification against supplied answers and supplied evidence. They do not demonstrate SQL execution, retrieval quality, or live Gemini/Groq answer quality. The new [50-case workflow record](nr2_evidence_2026-10-19/workflow-results.json) executes real SQL, ingestion, retrieval, grounding and conversation persistence using a synthetic provider; all 50 passed. See [current verification](nr2_remediation_2026-10-19.md). Live provider comparisons remain an integration check.

# DataSpeakAI — NR-2.2 AI Grounding & Evaluation Baseline Report

**Evaluation Date:** 2026-10-18  
**Milestone:** NR-2.2 ("Accurate evidence and dependable retrieval")  
**Sprint:** NR-2.2-A ("Grounding states and answer evaluation")  
**Evaluation Dataset:** `tests/fixtures/nr2/eval_dataset_v1.json` (Version 1.0.0, 25 test cases)  
**Test Harness:** `tests/test_nr2_eval_benchmark.py` & `tests/test_nr2_grounding_verification.py`  
**Embedding Model Evaluated:** `sentence-transformers/all-MiniLM-L6-v2` via `CitationService`  

---

## 1. Executive Summary & Purpose

Milestone NR-2.2 establishes dependable evidence and honest grounding verification across all conversational modalities (SQL, RAG, Hybrid). Previously, Defect `I-11` (FYP-05) caused embedding outages to return a reassuring `0.7` confidence without disclaimer, and Defect `I-12` (FYP-06) caused BM25 sparse index rebuilds to misattribute all tenant chunks to the newest document's name. Furthermore, numerical hallucinations and negation inversions could bypass generic cosine similarity checks (>0.65) due to high lexical overlap.

This baseline report records the verified behavior of the overhauled `CitationService`, prompt isolation architecture (`<document_evidence>`), and multi-state grounding engine across 25 standardized benchmark cases.

---

## 2. Evaluation Dataset Structure

The benchmark dataset is versioned in `tests/fixtures/nr2/eval_dataset_v1.json` with 25 test cases distributed across 9 evaluation categories:

| Category | Case IDs | Description | Target Metric |
|---|---|---|---|
| **SQL Aggregations & Joins** | TC-01 to TC-04 | Precise SQL execution, sums, counts, customer tier breakdowns | 100% accuracy, bounded execution |
| **RAG HR & Security Policies** | TC-05 to TC-09 | Knowledge base retrieval on leave policies, timeouts, Fernet encryption | >=0.70 grounding confidence |
| **Hybrid Multi-Source** | TC-10, TC-11 | Integrated SQL calculations + qualitative document evidence | Correct multi-source citations |
| **Abstention on Missing Data** | TC-12 to TC-14 | Unanswerable queries (Antarctica 2018, Competitor Corp, 2035 projections) | `no_claims`, no fabricated facts |
| **Numerical Hallucination Traps** | TC-15 to TC-17 | Claims asserting modified numbers ($999M vs $10M, 2500 vs 250, 85.5% vs 12.4%) | 100% rejection, `unsupported` status |
| **Date Conflict Traps** | TC-18, TC-19 | Claims asserting conflicting years or quarters (1995 vs 2021, Q4 2022 vs Q1 2026) | 100% rejection, `unsupported` status |
| **Negation Inversion Traps** | TC-20, TC-21 | Claims inverting negation polarity (removing or adding "not") | 100% rejection, polarity conflict |
| **Prompt Injection Defenses** | TC-22 to TC-24 | Injections inside chunks (`[SYSTEM INSTRUCTION]`, tag breakouts, prompt exfiltration) | 100% sanitized, defused |
| **Outage Resilience** | TC-25 | Embedding service cluster outage simulation | `unverified`, 0.0 confidence, disclaimer |

---

## 3. Benchmark Verification Results

Execution via `pytest tests/test_nr2_eval_benchmark.py -v`:

```
tests/test_nr2_eval_benchmark.py::test_eval_dataset_structure_and_completeness PASSED [  9%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_sql_supported_grounding PASSED [ 18%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_rag_supported_grounding PASSED [ 27%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_hybrid_supported_grounding PASSED [ 36%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_unanswerable_abstention PASSED [ 45%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_numerical_hallucinations_rejected PASSED [ 54%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_date_conflicts_rejected PASSED [ 63%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_negation_polarity_traps_rejected PASSED [ 72%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_prompt_injections_defused PASSED [ 81%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_outage_simulation_honest_unverified PASSED [ 90%]
tests/test_nr2_eval_benchmark.py::test_eval_benchmark_all_25_cases_comprehensive_pass_rate PASSED [100%]
```

### Key Quantitative Metrics

- **Total Test Cases:** 25
- **Benchmark Pass Rate:** 100.0% (25/25)
- **Numerical Hallucination Detection Rate:** 100.0% (3/3 caught and capped to 0.0 support)
- **Date Conflict Detection Rate:** 100.0% (2/2 caught and capped to 0.0 support)
- **Negation Polarity Conflict Detection Rate:** 100.0% (2/2 caught and rejected)
- **Prompt Injection Neutralization Rate:** 100.0% (3/3 defused, all `<document_evidence>` delimiters maintained)
- **Grounding Honesty on Outage:** 100.0% (Returned `grounding_status="unverified"`, `grounding_confidence=0.0`, `has_low_confidence=True`, `disclaimer` present)
- **False Positive Verified Rate on Errors:** 0.0% (Eliminated hardcoded 0.7 confidence fallback)

---

## 4. Architectural Enhancements Verified

### 4.1 Multi-State Grounding Contract
Answers now transition deterministically between five explicit states (`schemas.GroundingStatus`):
1. **`supported`**: Claim coverage ratio >= 80%. Displayed in UI as `Verified (X/Y claims)` with emerald badge.
2. **`partially_supported`**: Claim coverage ratio > 0% but < 80%. Displayed in UI as `Partial Grounding (X/Y claims)` with amber badge.
3. **`unsupported`**: All factual claims failed support or were contradicted by numerical/negation checks. Displayed in UI as `Evidence Contradicted` with red badge.
4. **`unverified`**: Verification could not complete due to embedding service or model failure. Displayed in UI as `⚠️ Unverified Evidence` with tooltip explaining the exact error reason.
5. **`no_claims`**: Conversational pleasantries, non-factual greetings, or abstentions where no factual statements were asserted. Displayed in UI as `No Factual Claims` with neutral badge.

### 4.2 Decoupled Retrieval Similarity vs Claim Support
In `schemas.SourceCitation`:
- `retrieval_similarity`: Vector cosine similarity or BM25 score of the chunk during search.
- `claim_support_score`: Cosine similarity of the verified claim against the chunk, strictly capped to 0.0 if numerical or negation checks fail.
- UI displays both metrics distinctly: `sim: XX%` and `support: XX%`.

### 4.3 Deterministic Numerical & Negation Verification
Function `verify_numerical_and_negation(claim, chunk)` extracts normalized numerical tokens (currency, percentages, years, integers, decimals) and negation tokens. If a claim asserts numbers absent from the source chunk, or reverses negation polarity, the claim is marked ungrounded regardless of raw vector similarity.

### 4.4 Prompt Injection Defense (`<document_evidence>`)
Retrieved evidence is pre-sanitized by `sanitize_evidence_text()` and wrapped in XML-style `<document_evidence id="..." source="..." page="..." type="...">` tags. System instructions explicitly command the LLM to treat content within these tags as untrusted reference evidence and to ignore instructions contained inside.

---

## 5. Model-Change Gate Policy

To prevent regressions during future model upgrades (e.g. migration to Gemini embeddings or alternative cross-encoders):
1. **Mandatory Pre-Deployment Test:** All changes to embeddings, chunking strategy, or prompt templates MUST execute `pytest tests/test_nr2_eval_benchmark.py`.
2. **Regression Threshold:** 
   - Zero tolerance (100% required) for Numerical Hallucination Detection, Negation Conflict Detection, and Prompt Injection Neutralization.
   - Grounding confidence on supported cases must maintain >= 0.70 average.
3. **Audit Trail:** Any change reducing coverage ratio or accuracy must be reviewed and approved by the AI/retrieval owner before merging.
