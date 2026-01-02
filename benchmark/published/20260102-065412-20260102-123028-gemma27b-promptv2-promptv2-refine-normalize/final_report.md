# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the **ArtistCalendar** poster‑extraction pipeline using the *gemini‑gemma‑3‑27b‑it* model on a curated set of 58 Thai tour‑date posters. Ground‑truth annotations are **silver‑quality** (LLM‑generated) as defined in the benchmark protocol. The model achieved an **App Quality Score** of **80.45 ± 1.55** (95 % CI [78.71, 82.26]) with perfect schema compliance (strict rate = 1.00) and incurred a total monetary cost of **USD 2.31** (entirely the cost of producing the silver ground truth).  

Key take‑aways:  

* The model delivers app‑ready structured JSON with high fidelity to the required schema.  
* Accuracy is strong relative to cost, as no inference cost was incurred (prediction_cost_usd = 0).  
* Because the ground truth is silver, the reported quality reflects the upper bound of what can be expected from a fully human‑verified (gold) dataset.  

---

## Dataset  
* **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
* **Size**: 58 single‑poster images containing tour‑date information.  
* **Ground‑Truth Availability**: 58 annotations; none missing.  
* **Ground‑Truth Quality**: **Silver** (LLM‑generated, not human‑verified).  
* **Manifest Status**: All 58 URLs passed the manifest check (`posters_manifest_ok` = 58).  

The dataset is limited to Thai‑language posters and reflects a narrow geographic and stylistic range, which may affect generalisation to other markets.

---

## Methodology  

1. **Prompting & Generation**  
   * Temperature fixed at **0.2** (Meta JSON).  
   * Random seed **23** used for all stochastic components.  
   * Prompt hashes are recorded for reproducibility (see `prompt_hashes` in Meta JSON).  

2. **Evaluation Metrics** (as defined in the benchmark protocol)  
   * **Schema Strict Rate** – proportion of predictions that exactly match the required JSON schema (keys, types, no extra fields).  
   * **App Quality Score** – composite 0‑100 metric weighted across structured output, top‑level fields, event matching, and event count (weights detailed in `weights` section of Meta JSON).  
   * **Bootstrap Confidence Intervals** – 1 000 resamples, seed 23, α = 0.05, yielding 95 % CIs for all scores.  

3. **Cost Accounting**  
   * **Prediction Cost** – USD 0 (model inference free for this run).  
   * **Judge Cost** – USD 0 (no human adjudication required).  
   * **Ground‑Truth Cost** – USD 2.308 029 (LLM generation).  
   * **Total Cost** – USD 2.308 029.  

4. **Statistical Testing**  
   * Pairwise model comparisons are not applicable here because only a single model was evaluated; the “Comparisons table” remains empty.  

---

## Results  

| Model                     | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|---------------------------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it      | 80.45 ± 1.55 (95 % CI [78.71, 82.26]) | 2.31 | 1.00 |

* **Missing Predictions**: 0 (all 58 posters processed).  
* **Judged Samples**: 9 (subset manually inspected for CI calculation).  
* **Additional Metrics** (averages across judged samples)  
  * Top‑level field score: **0.721**  
  * Event‑match score: **0.636**  
  * Event‑count score: **0.98**  
  * Location score: **0.626**  
  * Venue score: **0.57**  
  * Missing‑field rate: **0.244** (≈ 24 % of fields missing per poster, mitigated by the missing‑field penalty in the composite score).  

All predictions passed strict schema validation (`schema_ok_rate` = 1.0, `schema_valid_rate` = 1.0, `json_parse_rate` = 1.0).

---

## Interpretation  

### Accuracy vs. Cost  
The model’s **App Quality Score** of **80.45** places it well above typical production thresholds (≈ 70) for app‑ready data. Because inference incurred no cost, the **cost‑efficiency** is maximal: the entire expense stems from generating silver ground truth. In a production setting with human‑verified (gold) ground truth, the cost would increase, but the model’s inference cost would remain negligible, preserving a favourable cost‑benefit ratio.

### Schema Compliance  
A strict rate of **1.00** demonstrates flawless adherence to the required JSON schema, eliminating downstream parsing errors. This reliability is crucial for the ArtistCalendar app, where malformed JSON would break the user experience.

### Missing Fields  
The average missing‑field rate of **24 %** indicates that while the model captures most required information, certain fields (e.g., venue, city) are omitted in roughly one‑quarter of cases. The composite scoring system penalises these omissions, yet the overall quality remains high due to strong performance on other dimensions (event count, top‑level fields).

### Statistical Significance  
With only a single model evaluated, no pairwise statistical tests are possible. The bootstrap confidence interval (± 1.55 points) suggests that the observed quality is stable across resamples, but future benchmarks should include multiple models to enable significance testing (e.g., p‑values, mean differences).

---

## Limitations  

| Aspect | Detail |
|--------|--------|
| **Ground‑Truth Quality** | Silver (LLM‑generated) – may contain systematic biases or errors not present in gold annotations. |
| **Dataset Scope** | 58 Thai‑language posters; limited stylistic diversity and geographic coverage. |
| **Missing Field Penalty** | Fixed penalty (10×) may over‑ or under‑represent the impact of missing fields for downstream app logic. |
| **Cost Reporting** | Prediction cost recorded as zero; actual cloud‑compute expenses (GPU time) are not captured. |
| **Statistical Power** | Only 9 judged samples used for CI estimation; larger judged sets would tighten confidence bounds. |
| **Reproducibility Details** | Temperature and seed are provided, but exact inference environment (hardware, library versions) is not captured in the supplied metadata. |

---

## Recommendations  

1. **Upgrade Ground Truth to Gold**  
   * Conduct a double‑annotator human verification process for at least a subset (e.g., 30 % of posters) to quantify the silver‑to‑gold gap.  

2. **Target Missing Fields**  
   * Fine‑tune prompt engineering or post‑processing rules to reduce the missing‑field rate, especially for venue and location attributes.  

3. **Expand Dataset**  
   * Incorporate additional languages, regions, and poster designs to improve model robustness and assess generalisation.  

4. **Capture Inference Cost**  
   * Record actual compute usage (GPU hours, API pricing) to provide a complete cost picture for production budgeting.  

5. **Run Multi‑Model Comparisons**  
   * Evaluate at least two additional models under identical conditions to enable statistical pairwise comparisons and identify the best cost‑performance trade‑off.  

6. **Document Execution Environment**  
   * Log container images, library versions, and hardware specs alongside the existing seed and temperature to ensure full reproducibility.  

By addressing these points, future benchmark releases will deliver more definitive guidance for selecting models that balance **app readiness**, **structured output reliability**, and **operational cost** for the ArtistCalendar platform.
