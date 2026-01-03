# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the ability of **gemini‑gemma‑3‑27b‑it** to extract structured tour‑event information from 58 Thai concert‑poster images for the **ArtistCalendar** application. Using a **silver‑quality** ground‑truth set (human‑verified data not available), the model achieved an **App Quality Score** of **83.75 ± 1.63** (95 % CI = 81.96–85.59) with perfect schema compliance (schema strict rate = 1.00). The total monetary cost of the run was **USD 2.31**, entirely attributable to the creation of the silver ground‑truth; model inference incurred no cost.  

Key take‑aways:  

* The model delivers app‑ready JSON output with high field‑level accuracy while remaining cost‑neutral for inference.  
* Schema adherence is flawless, eliminating downstream validation failures.  
* Because the ground truth is silver, the reported quality reflects a best‑case estimate; a gold‑standard evaluation could shift the score.  

---

## Dataset  
* **Source**: Instagram URLs listed in `docs/test_poster_urls.txt`.  
* **Size**: 58 single‑poster images containing tour‑date information.  
* **Ground‑Truth Quality**: **Silver** (human‑verified gold not available).  
* **Manifest**: All 58 URLs successfully downloaded (`posters_manifest_ok` = 58).  
* **Coverage**: 100 % of the dataset has ground‑truth annotations (`ground_truth_available` = 58, `missing_ground_truth` = 0).  

The dataset focuses on Thai‑language posters, with occasional English text, and reflects a realistic mix of typography and layout styles encountered by the ArtistCalendar app.

---

## Methodology  

| Component | Detail |
|-----------|--------|
| **Prompting** | Fixed prompt hashes (see `prompt_hashes` in meta JSON) were used for OCR, parsing, and prediction. |
| **Model Settings** | Temperature = 0.2, seed = 23 (consistent across runs). |
| **Scoring** | App quality score (0‑100) combines weighted sub‑metrics: structured output (0.4), event‑match (0.35), top‑level fields (0.15), event‑count (0.1). Weights are defined in the `weights` section of the meta JSON. |
| **Schema Checks** | Three rates recorded: `schema_ok_rate`, `schema_valid_rate`, and `schema_strict_rate`. All must be 1.0 for “app‑ready” output. |
| **Statistical Reliability** | Bootstrap with 1 000 resamples, seed = 23, α = 0.05. 95 % confidence intervals reported for the app quality score. |
| **Cost Accounting** | `prediction_cost_usd` = 0 (free inference). `ground_truth_cost_usd` = 2.308 USD (silver annotation). `total_cost_usd` = 2.308 USD. |
| **Evaluation Metrics** | • **Avg Top‑Level Score** = 0.738  <br>• **Avg Event‑Match Score** = 0.736  <br>• **Avg Event‑Count Score** = 0.986  <br>• **Avg Location Score** = 0.744  <br>• **Avg Venue Score** = 0.667  <br>• **Avg Date F1** = 0.748  <br>• **Missing‑Field Rate** = 0.294 (penalised by the missing‑field penalty of 10.0). |

No predictions were missing (`missing_predictions` = 0) and all 58 predictions were judged.

---

## Results  

### Summary Table  

| Model | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|-------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it | **83.75** (95 % CI = 81.96–85.59) | **2.31** | **1.00** |

*All other rates (schema OK, schema valid, JSON parse) are also 1.00.*

### Detailed Metrics  

| Metric | Value |
|--------|-------|
| Posters evaluated | 58 |
| Avg. top‑level field score | 0.738 |
| Avg. event‑match score | 0.736 |
| Avg. event‑count score | 0.986 |
| Avg. location score | 0.744 |
| Avg. venue score | 0.667 |
| Avg. date F1 | 0.748 |
| Missing‑field penalty (average) | 0.294 |
| Std. dev. of app quality | 6.997 |

The high event‑count score (0.986) indicates that the model almost always predicts the correct number of events per poster, while venue and location scores are modestly lower, reflecting the typical OCR difficulty with Thai script and varied poster layouts.

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality, app‑ready JSON** at **zero inference cost**, making it an attractive candidate for production deployment where scaling to thousands of daily posters is required. The modest total cost (USD 2.31) stems solely from the creation of silver ground truth; in a production pipeline, this cost would be amortised over many inference runs.

### Trade‑offs in Field Accuracy  
* **Top‑level fields** (artist name, Instagram handle, tour name, contact info, source month) achieve a combined score of 0.738, indicating reliable extraction of the most visible information.  
* **Event‑level fields** (date, venue, city, province) show slightly lower performance (venue = 0.667, location = 0.744, date F1 = 0.748). These are the primary sources of the missing‑field penalty (0.294). Improving OCR for Thai script or adding a post‑processing refinement step could raise these scores without affecting cost.  

### Statistical Significance  
Because only a single model was evaluated, pairwise statistical comparisons are **not applicable** (the “Model comparisons” table is empty). The bootstrap confidence interval around the app quality score (±1.63) provides a reliable estimate of variability across the 58 posters.

### Reliability of Structured Output  
A **schema strict rate of 1.00** means every JSON output exactly matches the required keys and data types, eliminating downstream parsing errors. Combined with a perfect JSON parse rate (1.00), the model’s output can be ingested directly by the ArtistCalendar backend.

---

## Limitations  

1. **Ground‑Truth Quality** – The benchmark uses **silver** annotations; human‑verified gold data could reveal systematic biases or errors not captured here.  
2. **Dataset Size & Diversity** – Only 58 posters, all from Thailand, limit generalisability to other regions, languages, or poster designs.  
3. **Missing‑Field Penalty** – The penalty (10×) heavily influences the composite score; alternative weighting could change the ranking.  
4. **Cost Reporting** – Model inference cost is recorded as zero because the provider offered free access; real‑world deployments on paid APIs may incur charges.  
5. **Statistical Power** – With a single model, we cannot assess relative performance or statistical significance across alternatives.  

---

## Recommendations  

1. **Upgrade Ground Truth to Gold** – Conduct dual‑annotator human verification for at least a subset (e.g., 30 % of posters) to quantify the silver‑to‑gold gap and adjust the app quality score accordingly.  
2. **Target Event‑Level Improvements** – Implement a dedicated Thai OCR fine‑tuning step or a post‑processing validator for venue and location fields to reduce the missing‑field penalty.  
3. **Expand the Dataset** – Add 100–200 more posters covering varied typographies, multilingual text, and different geographic regions to improve robustness.  
4. **Cost Monitoring** – If moving to a paid LLM endpoint, repeat the benchmark with the actual inference cost to evaluate the cost‑accuracy frontier.  
5. **Run Comparative Experiments** – Evaluate additional models (e.g., Claude‑3‑Opus, GPT‑4‑Turbo) under identical settings to populate the “Model comparisons” table and identify statistically significant differences.  

By addressing these points, the ArtistCalendar team can confidently move the **gemini‑gemma‑3‑27b‑it** model—or a superior alternative—into production, delivering reliable, low‑cost structured data extraction for Thai tour posters.
