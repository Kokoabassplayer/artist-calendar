# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates **gemini‑gemma‑3‑27b‑it** on the ArtistCalendar “Thai Tour Poster” extraction task. Using a **silver‑quality** ground‑truth set (human‑verified data not available), the model achieved an **App Quality Score** of **83.15 ± 1.71 (95 % CI)** while incurring a total cost of **USD 2.31** for the entire run. Schema compliance was perfect (strict‑rate = 1.0). The results suggest the model is ready for production‑level integration, delivering high‑fidelity structured JSON at negligible inference cost.

---

## Dataset  
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
- **Content**: 58 single‑image Thai tour‑date posters containing artist name, tour name, dates, venues, and contact information.  
- **Ground‑Truth Quality**: **Silver** (generated via LLM‑assisted annotation; human verification not performed).  
- **Availability**: All 58 ground‑truth records are present; no missing entries.  

The dataset is versioned by the SHA‑256 hash of the URL list and manifest, recorded in `benchmark/report/meta.json`.

---

## Methodology  

| Step | Description |
|------|-------------|
| **Prompting** | Fixed temperature = 0.2; prompt hashes recorded (e.g., `benchmark/prompts/predict.txt`). |
| **Randomness Control** | Seed = 23 for model sampling and for bootstrap resampling. |
| **Prediction** | Model generated JSON for each poster; all predictions parsed successfully (`json_parse_rate = 1.0`). |
| **Schema Validation** | Strict schema check (keys, types, no extra fields) – `schema_strict_rate = 1.0`. |
| **Scoring** | Composite **App Quality Score** (0‑100) computed from weighted sub‑metrics (structured, event‑match, top‑level, event‑count) using weights from the meta JSON. |
| **Bootstrap** | 1 000 resamples, seed = 23, α = 0.05 → 95 % confidence intervals for all metrics. |
| **Cost Accounting** | Prediction cost = USD 0 (model run on free tier); judge cost = USD 0; ground‑truth generation cost = USD 2.308029. Total = USD 2.308029. |

No human adjudication was performed; therefore the ground‑truth is labeled **silver** and the report explicitly notes this limitation.

---

## Results  

| Model | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|-------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it | **83.15** (95 % CI [81.51, 84.92]) | **2.31** | **1.0** |

Additional performance details (averaged across the 58 posters):

| Metric | Value |
|--------|-------|
| Avg. Top‑Level Score | 0.734 |
| Avg. Event‑Match Score | 0.71 |
| Avg. Event‑Count Score | 0.987 |
| Avg. Location Score | 0.658 |
| Avg. Venue Score | 0.671 |
| Avg. Missing‑Field Rate | 0.258 |
| Avg. Event Difference | 0.207 |
| Avg. Date F1 | 0.748 |
| Schema OK Rate | 1.0 |
| JSON Parse Rate | 1.0 |

All predictions were syntactically valid JSON and adhered exactly to the required schema.

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (score ≈ 83) while the **inference cost is effectively zero**; the only expense is the one‑time generation of silver ground truth (USD 2.31). This cost profile is highly favorable for scaling the ArtistCalendar app, where thousands of posters may be processed daily.

### Trade‑offs in Silver Ground Truth  
Because the reference data is silver rather than gold, the absolute App Quality Score may be inflated or deflated relative to a human‑verified baseline. The missing‑field penalty (10 × rate) contributed to a modest reduction in score (missing‑field rate ≈ 0.26). Nonetheless, the **strict schema compliance** (1.0) indicates the model reliably produces parsable JSON, a critical requirement for downstream app pipelines.

### Statistical Significance  
Only a single model was evaluated; therefore pairwise bootstrap comparisons are **not applicable** (the “Model comparisons” table is empty). The narrow confidence interval (± 1.7 points) demonstrates **stable performance** across bootstrap samples, suggesting that the observed score is unlikely to be a sampling artifact.

---

## Limitations  

1. **Ground‑Truth Quality** – Silver annotations may contain systematic errors (e.g., mis‑identified venues or dates). Results should be re‑validated against a gold‑standard set before final production release.  
2. **Dataset Size & Diversity** – 58 posters represent a limited slice of Thai poster designs; OCR difficulty varies with font, layout, and image quality, potentially biasing performance estimates.  
3. **Domain Specificity** – The benchmark focuses on Thai‑language posters; performance on other languages or regions is unknown.  
4. **Cost Reporting** – Prediction cost is recorded as zero because the model was run on a free tier; actual cloud‑provider pricing could differ.  

---

## Recommendations  

1. **Human Verification** – Create a gold‑standard subset (≥ 20 posters) with dual annotator adjudication to confirm the silver‑based App Quality Score.  
2. **Cost Monitoring** – When moving to a paid inference environment, log actual token usage to refine cost estimates.  
3. **Model Selection** – Given the perfect schema compliance and strong quality score, **gemini‑gemma‑3‑27b‑it** is a viable candidate for production. Consider testing additional models (e.g., GPT‑4o) to ensure the chosen model remains optimal as the dataset expands.  
4. **Robustness Checks** – Augment the benchmark with posters featuring extreme typography, low contrast, or multi‑panel layouts to stress‑test OCR and extraction pipelines.  
5. **Continuous Evaluation** – Integrate automated nightly runs on newly added URLs, preserving the same temperature (0.2), seed (23), and bootstrap settings to track drift over time.  

---

*Report generated on 2026‑01‑03T15:31:38+00:00. All reproducibility parameters (temperature = 0.2, seed = 23, bootstrap = 1000 samples) are documented in the accompanying Meta JSON.*
