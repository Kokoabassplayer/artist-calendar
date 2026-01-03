# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the **gemini‑gemma‑3‑27b‑it** model on the ArtistCalendar “Thai Tour Poster” extraction task. Using a **silver‑quality** human‑verified ground‑truth set (58 posters), the model achieved an **App Quality Score** of **79.52 ± 1.74** (95 % CI [77.72, 81.46]) and an **App Core Score** of **77.69 ± 1.66** (95 % CI [75.58, 79.91]). Schema compliance was perfect (strict‑rate = 1.0) and the total monetary cost of the run was **$2.31 USD**, entirely attributable to ground‑truth generation. The model therefore delivers app‑ready structured JSON at a high accuracy‑to‑cost ratio, suitable for production deployment pending further validation on larger datasets.

---

## Dataset  
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
- **Content**: 58 single‑image Thai tour‑date posters containing artist name, tour name, dates, venues, and contact information.  
- **Ground‑Truth Quality**: **Silver** (human‑verified but not double‑annotated gold standard).  
- **Availability**: Ground‑truth JSON files are present for all 58 items; no missing predictions or missing ground‑truth entries.  

---

## Methodology  

| Aspect | Detail |
|--------|--------|
| **Prompting** | Fixed prompt set (see `benchmark/prompts/` hashes). |
| **Model Settings** | Temperature = 0.2, seed = 23 (applied uniformly). |
| **Scoring** | Composite **App Quality** (weights: structured 0.4, event_match 0.35, top_level 0.15, event_count 0.1) and **App Core** (same but event_match limited to core fields). Missing‑field penalty = 10. |
| **Schema Checks** | Strict key‑type validation, JSON parse validation, and schema‑strict rate computed per run. |
| **Statistical Reliability** | 1,000 bootstrap resamples, seed = 23, α = 0.05 → 95 % confidence intervals for all scores. |
| **Cost Accounting** | Prediction cost = $0 (model run on free tier), judge cost = $0, ground‑truth cost = $2.308 USD. |
| **Reproducibility** | All run metadata (temperature, seed, bootstrap parameters, prompt hashes, scoring weights) recorded in `benchmark/report/meta.json`. The same configuration can be re‑executed with `benchmark/benchmark.py publish`. |

---

## Results  

| Model | App Quality Score | App Core Score | Total Cost (USD) | Schema Strict Rate |
|-------|-------------------|----------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it | 79.52 ± 1.74 (95 % CI [77.72, 81.46]) | 77.69 ± 1.66 (95 % CI [75.58, 79.91]) | 2.31 | 1.0 |

*All rates (schema_ok, schema_valid, json_parse) were 1.0, indicating flawless structural compliance.*

### Additional Metrics (averages across the 58 posters)

| Metric | Value |
|--------|-------|
| Avg. Top‑Level Score | 0.746 |
| Avg. Event Match Score | 0.652 |
| Avg. Core Event Match Score | 0.600 |
| Avg. Event Count Score | 0.981 |
| Avg. Location Score | 0.669 |
| Avg. Venue Score | 0.491 |
| Avg. Missing‑Field Rate | 0.43 (≈ 43 % of events missing at least one required field) |
| Avg. Event‑Count Difference | 0.397 |
| Avg. Date F1 | 0.687 |

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (≈ 80 % composite score) while incurring **negligible prediction cost**. The only expense stems from creating the silver ground‑truth, amounting to **$2.31 USD** for the entire run. This cost profile is highly favorable for scaling the extraction pipeline to thousands of posters, where per‑item prediction cost would remain effectively zero.

### Schema Reliability  
A **schema strict rate of 1.0** demonstrates that the model consistently produces JSON that exactly matches the expected schema, eliminating downstream validation failures. This reliability is critical for the ArtistCalendar app, which expects deterministic field types for downstream scheduling and notification logic.

### Event‑Level Performance  
- **Event match (0.652)** and **core event match (0.600)** indicate that roughly two‑thirds of predicted events align with the ground truth on key attributes (date, venue, city, province, country).  
- The **event count score (0.981)** shows the model almost always predicts the correct number of events per poster, reducing the risk of missing entire shows.  
- The **missing‑field rate (0.43)** reveals that while the model often includes most fields, a substantial minority of events lack at least one required attribute (e.g., venue or date). This is the primary source of score reduction and should be targeted for improvement (e.g., enhanced OCR preprocessing or prompt refinement).

### Statistical Significance  
No pairwise model comparisons are available in the supplied data; the “Model comparisons” table is empty. Consequently, we cannot claim statistically significant superiority over alternative models. However, the narrow bootstrap confidence intervals (≈ ± 2 points) suggest the reported scores are stable across resampling.

---

## Limitations  

1. **Ground‑Truth Quality** – The benchmark uses **silver** ground truth. While human‑verified, it lacks the double‑annotation and adjudication required for a gold standard, potentially inflating or deflating scores.  
2. **Dataset Size & Diversity** – Only 58 Thai‑language posters were evaluated, limiting generalizability to other languages, regions, or poster designs.  
3. **Missing‑Field Penalty** – The penalty weight (10×) heavily influences the composite scores; alternative weighting could shift the interpretation of “accuracy.”  
4. **Cost Reporting** – Prediction cost is recorded as $0 because the model was run on a free tier; real‑world deployment on paid infrastructure may introduce non‑trivial costs.  
5. **Statistical Comparisons** – No alternative models were benchmarked in this run, so relative performance cannot be quantified.  

---

## Recommendations  

1. **Upgrade Ground Truth to Gold** – Conduct double annotation with adjudication for a subset (e.g., 30 % of posters) to quantify any bias introduced by silver data.  
2. **Target Missing Fields** – Investigate OCR error patterns that lead to omitted dates or venues; consider integrating a post‑processing validation step that flags incomplete events for manual review.  
3. **Expand Dataset** – Add at least 200 more posters covering varied typographies, bilingual text, and different geographic regions to stress‑test the model’s robustness.  
4. **Cost Modeling** – Simulate production‑scale inference on the intended cloud provider to obtain realistic per‑item cost estimates and assess budget impact.  
5. **Model Ensemble or Prompt Tuning** – Experiment with a lightweight ensemble (e.g., gemini‑gemma‑3‑27b‑it + a smaller open‑source model) or refined prompts to see if event‑match scores can be pushed above 0.75 without sacrificing schema compliance.  

---

**Conclusion** – The gemini‑gemma‑3‑27b‑it model demonstrates strong, app‑ready extraction performance on the current silver‑ground‑truth Thai poster benchmark, with perfect schema adherence and minimal monetary cost. Addressing the identified missing‑field issue and moving toward gold‑standard validation will further solidify confidence for production deployment.
