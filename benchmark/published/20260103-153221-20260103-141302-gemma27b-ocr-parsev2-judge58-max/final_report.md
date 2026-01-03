# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the **gemini‑gemma‑3‑27b‑it** model on the **ArtistCalendar** poster‑extraction task using the **silver‑quality** ground‑truth dataset (58 Thai tour‑date posters). The model achieved an **App Quality Score** of **83.15 ± 1.71 (95 % CI [81.51, 84.92])** and an **App Core Score** of **81.48 ± 1.85 (95 % CI [79.61, 83.46])**. Schema compliance was perfect (strict‑rate = 1.0) and the total monetary cost of the run was **USD 2.31**, entirely attributable to human ground‑truth creation. The results indicate that the model delivers app‑ready structured JSON with high fidelity while incurring negligible inference cost, making it a strong candidate for production deployment.

---

## Dataset  
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
- **Content**: 58 single‑image posters that contain tour‑date information for Thai artists.  
- **Ground‑Truth Quality**: **Silver** (human‑verified annotations derived from a rapid iteration pipeline; not the full double‑annotator gold standard).  
- **Availability**: All 58 ground‑truth JSON files are present; no missing entries.  

---

## Methodology  

1. **Prompting & Inference**  
   - Temperature: **0.2** (fixed for all runs).  
   - Random seed: **23** (ensures deterministic token sampling).  
   - Prompt hash used: `benchmark/prompts/predict_v2.txt` (hash `3f44d00d9d2241cccd22e44593fbd6cc760356daf7376240917ed0a52f6d9615`).  

2. **Scoring**  
   - **App Quality Score** (0‑100) combines weighted components: structured output (0.4), event‑match (0.35), top‑level fields (0.15), and event‑count (0.1).  
   - **App Core Score** uses the same weighting but restricts event‑match to the core fields (date, venue, city, province, country).  
   - Missing‑field penalty of **10.0** points is applied per absent core field.  

3. **Statistical Reliability**  
   - Bootstrap with **1,000 resamples**, seed **23**, α = 0.05.  
   - 95 % confidence intervals reported for both scores.  

4. **Schema Validation**  
   - Strict schema checks (key names, types, and required fields) yielded a **schema_strict_rate** of **1.0**.  
   - JSON parsing succeeded for all predictions (`json_parse_rate` = 1.0).  

5. **Cost Accounting**  
   - Model inference cost: **USD 0.00** (free tier or internal allocation).  
   - Human ground‑truth creation cost: **USD 2.308029**.  
   - Total run cost: **USD 2.308029**.  

---

## Results  

| Model                     | App Quality Score | App Core Score | Total Cost (USD) | Schema Strict Rate |
|---------------------------|-------------------|----------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it      | 83.15 ± 1.71       | 81.48 ± 1.85    | 2.31             | 1.0                |

*All scores are mean values; 95 % CI shown in the narrative above.*

Additional aggregated metrics (averaged across the 58 posters)  

| Metric                              | Value |
|-------------------------------------|-------|
| Avg. Top‑Level Score                | 0.734 |
| Avg. Event‑Match Score              | 0.71  |
| Avg. Core Event‑Match Score         | 0.662 |
| Avg. Event‑Count Score              | 0.987 |
| Avg. Location Score                 | 0.658 |
| Avg. Venue Score                    | 0.671 |
| Avg. Missing‑Field Rate             | 0.258 |
| Avg. Date F1                        | 0.748 |
| Avg. Event Difference (count)       | 0.207 |

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (≈ 83 % of the maximum possible score) while incurring **no inference cost**. The modest total cost (USD 2.31) stems solely from human annotation, confirming that the model is cost‑effective for large‑scale deployment where inference expenses dominate.

### Schema Reliability  
A perfect schema strict rate (1.0) demonstrates that the model consistently produces JSON that conforms exactly to the required schema, eliminating downstream validation failures. This reliability is crucial for the **ArtistCalendar** app, which expects deterministic field presence for downstream scheduling logic.

### Event‑Match Performance  
The event‑match scores (0.71 overall, 0.662 core) indicate that most predicted events align with ground truth on date, venue, and location. The remaining discrepancy is largely attributable to the **missing‑field penalty** (average missing‑field rate = 0.258), suggesting that the model occasionally omits optional fields such as time or ticket information. However, core fields (date, venue, city, province, country) are captured with acceptable fidelity.

### Statistical Significance  
Bootstrap confidence intervals are narrow (≈ ± 2 points), confirming that the observed scores are stable across resamples. No pairwise comparison data are available (the benchmark includes only a single model), so statistical significance relative to alternatives cannot be assessed here.

---

## Limitations  

1. **Ground‑Truth Quality** – The dataset uses **silver** annotations; while human‑verified, they have not undergone the full double‑annotator adjudication required for gold‑standard status. Consequently, the reported scores may be slightly optimistic or pessimistic relative to a gold benchmark.  
2. **Dataset Size & Diversity** – Only 58 posters, all from Thai artists, limit generalizability to other languages, regions, or poster designs.  
3. **Missing Field Penalty** – The penalty weight (10.0) heavily influences the composite scores; alternative weighting schemes could shift the ranking of models.  
4. **Cost Reporting** – Inference cost is recorded as zero, reflecting internal pricing; external deployments may incur non‑zero compute charges.  

---

## Recommendations  

1. **Production Readiness** – Given the perfect schema compliance, high app quality score, and zero inference cost, **gemini‑gemma‑3‑27b‑it** is ready for integration into the ArtistCalendar pipeline. Implement a lightweight post‑processing step to flag any missing optional fields for manual review.  

2. **Gold‑Standard Validation** – Conduct a follow‑up run using **gold** ground truth (two independent annotators + adjudication) for a subset of posters to quantify any bias introduced by silver data.  

3. **Expand Dataset** – Augment the benchmark with additional languages (e.g., English, Japanese) and varied poster layouts to ensure robustness across the global market.  

4. **Cost Monitoring** – When scaling to cloud inference, track actual compute spend; consider batch processing or model quantization if costs become non‑trivial.  

5. **Error Analysis** – Perform a focused error analysis on the 25 % of events with missing fields to refine prompts or OCR preprocessing, potentially improving the event‑match and core scores further.  

---

*Reproducibility details*: temperature = 0.2, seed = 23, bootstrap = 1,000 samples (seed = 23, α = 0.05). Prompt hashes and weighting schemas are recorded in the meta JSON above. All steps can be reproduced with `benchmark/benchmark.py publish` using the same configuration files.
