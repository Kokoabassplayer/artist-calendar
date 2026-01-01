# Final Benchmark Report

## Executive Summary
This benchmark evaluates **poster-to-structured-JSON extraction** for the ArtistCalendar app using a Thai tour poster dataset. Two vision-language models were tested on 58 posters with **silver** ground truth (LLM-generated or otherwise non-human-adjudicated per protocol), which is suitable for rapid iteration but **not** for final publish-grade accuracy claims.

Overall app quality is similar across models: **gemini-gemma-3-27b-it** achieves the highest mean **app_quality_score** (50.3) versus **ollama-qwen2.5vl_3b** (47.48), but the difference is **not statistically significant** (p=0.124). Structured-output reliability is a key blocker: both models have **schema_strict_rate = 0.0** and **schema_valid_rate = 0.0**, despite high “schema OK” rates, indicating outputs often parse but do not strictly conform to the required schema.

## Dataset
- **Dataset size**: 58 posters
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt` (single-image posters containing tour-date info)
- **Language/region**: primarily Thai / Thailand
- **Ground truth availability**: 58/58 available; missing ground truth: 0
- **Ground truth quality level**: **silver**
  - **Implication**: results are indicative for engineering iteration but are limited for product decisions requiring human-verified correctness (the protocol’s publishable standard is gold with two annotators + adjudication).
- **Judged examples**:
  - gemini-gemma-3-27b-it: 57 judged (1 missing prediction)
  - ollama-qwen2.5vl_3b: 56 judged (2 missing predictions)

## Methodology
### Task
Models extract structured tour information from poster images into a JSON schema defined in `benchmark/prompts/ground_truth.txt`, emphasizing **app-ready outputs**.

### Metrics (key)
- **App quality score (0–100)**: weighted composite of:
  - structured output (weight 0.4)
  - event match (0.35)
  - top-level fields (0.15)
  - event count (0.1)
- **Schema strict rate**: exact schema keys and types with no extra fields (critical for production ingestion).
- **JSON parse rate**: fraction of outputs parseable as JSON.
- Additional diagnostic components reported include event matching score, location/venue scores, missing field rate, and event count discrepancy.

### Statistical testing
- **Bootstrap CIs**: 1,000 resamples, alpha 0.05, seed 23
- Pairwise comparison reports mean difference, 95% CI, and p-value.

### Reproducibility (from Meta JSON)
- **Generated at**: 2025-12-31T22:18:30+00:00  
- **Temperature**: 0.1  
- **Seed values**: [23]  
- **Bootstrap**: 1,000 samples, seed 23, alpha 0.05  
- **Prompt hashes recorded** for predict/judge/ground-truth/interpret prompts.
- **Max output caps**: not available (not present in Meta JSON).

## Results
### Summary table
| model | app_quality_score | total_cost_usd | schema_strict_rate |
|---|---:|---:|---:|
| gemini-gemma-3-27b-it | 50.3 | 3.505944 | 0.0 |
| ollama-qwen2.5vl_3b | 47.48 | 3.417351 | 0.0 |

### Detailed highlights
**gemini-gemma-3-27b-it**
- Posters: 58; missing predictions: 1; judged: 57  
- App quality: **50.3** (95% CI **47.53–52.84**), std 9.887  
- JSON parse rate: **0.983**
- Schema: schema_ok_rate **1.0**, but schema_valid_rate **0.0** and schema_strict_rate **0.0**
- Subscores: top-level 0.700; event match 0.642; event count 0.969; location 0.686; venue 0.483  
- Missing field rate: 0.431; avg event diff: 0.379; avg_date_f1: 0.0  
- Costs (USD): prediction 0; judge 1.197915; ground truth 2.308029; **total 3.505944**

**ollama-qwen2.5vl_3b**
- Posters: 58; missing predictions: 2; judged: 56  
- App quality: **47.48** (95% CI **44.4–49.99**), std 11.207  
- JSON parse rate: **0.966**
- Schema: schema_ok_rate **1.0**, but schema_valid_rate **0.0** and schema_strict_rate **0.0**
- Subscores: top-level 0.742; event match 0.560; event count 0.893; location 0.528; venue 0.357  
- Missing field rate: 0.412; avg event diff: 1.724; avg_date_f1: 0.0  
- Costs (USD): prediction 0; judge 1.109322; ground truth 2.308029; **total 3.417351**

### Model comparison (bootstrap)
- gemini-gemma-3-27b-it vs ollama-qwen2.5vl_3b  
  - Mean diff: **+2.824**
  - 95% CI: **-0.509–6.688**
  - p-value: **0.124**
  - Significant: **False**

## Interpretation
### App readiness and structured output reliability
From an application-integration perspective, the most important finding is **structured output non-compliance**: both models achieve **schema_strict_rate = 0.0** and **schema_valid_rate = 0.0**. Even with strong JSON parse rates (~0.97–0.98) and schema_ok_rate of 1.0, the outputs are not reliably conforming to the strict schema expected by downstream components. This is a substantial barrier to production use without a repair/validation layer.

### Accuracy vs cost tradeoffs
Total benchmark costs are similar (USD **3.51** vs **3.42**), driven by judge and ground-truth costs; **prediction_cost_usd is 0 for both** (as recorded), so this run cannot establish real inference cost differences. On quality, gemini-gemma-3-27b-it trends higher in:
- overall app quality (50.3 vs 47.48),
- event matching (0.642 vs 0.560),
- location and venue subscores.

However, the confidence intervals overlap and the pairwise test is **not statistically significant** (p=0.124). Practically: choose gemini-gemma-3-27b-it if you want a modest quality edge, but do not treat it as a proven improvement.

### Field-level considerations
- **avg_date_f1 = 0.0 for both models**, which suggests date extraction/matching is failing under the current scoring/normalization regime or outputs are systematically misformatted relative to evaluation expectations. Given dates are core to tour ingestion, this strongly reduces app readiness.
- Event count accuracy is relatively strong for gemini (0.969) and weaker for qwen (0.893), consistent with qwen’s higher avg_event_diff (1.724 vs 0.379).

## Limitations
- **Silver ground truth**: by protocol, silver labels are not human-adjudicated; this limits the validity of absolute accuracy claims and can bias metrics if the “truth” contains extraction errors or inconsistent formatting.
- **Schema validity/strictness both 0.0**: metrics indicate the current prompting or post-processing is insufficient for strict schema compliance, making quality scores less actionable for production until structured reliability is fixed.
- **Max output caps**: not available in the recorded meta; output truncation risk cannot be assessed from this report.
- **Dataset scope**: 58 Thai posters; results may not generalize beyond Thai-centric poster styles or to other regions and typography.

## Recommendations
1. **Prioritize strict schema compliance**: introduce a deterministic JSON schema enforcement step (validator + auto-repair) and/or revise prompts to eliminate extra keys/type mismatches, targeting **schema_strict_rate > 0.95** before further model selection.
2. **Investigate date extraction failure (avg_date_f1 = 0.0)**: audit predicted date formats versus ground truth expectations and normalize dates consistently (e.g., Thai month names, Buddhist Era vs Gregorian) within the evaluation pipeline and prompts.
3. **Model choice for iteration**: prefer **gemini-gemma-3-27b-it** as the current best performer on app_quality_score and event matching, but treat the improvement as **non-significant** statistically in this run.
4. **Upgrade to gold ground truth for publication-grade conclusions**: follow the protocol (two annotators + adjudication) and report inter-annotator agreement; re-run comparisons once gold labels are available.
5. **Track real inference costs**: prediction_cost_usd is recorded as 0 for both; production selection needs measured inference cost/latency under consistent deployment settings.
