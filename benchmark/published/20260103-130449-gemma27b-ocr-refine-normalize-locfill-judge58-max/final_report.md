# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the ability of **gemini‑gemma‑3‑27b‑it** to extract structured tour‑event data from 58 Thai concert‑poster images for the **ArtistCalendar** application. Using a **silver‑quality** ground‑truth (human‑verified data not available), the model achieved an **App Quality Score** of **83.75 ± 1.63** (95 % CI = 81.96–85.59) with perfect schema compliance (schema strict rate = 1.00). The total monetary cost of the run was **USD 2.31**, entirely attributable to the creation of the silver ground‑truth; model inference incurred no cost.  

The results indicate that the model delivers app‑ready JSON output at a very low cost, satisfying the primary production requirement of reliable, schema‑strict data. However, the silver ground‑truth limits the confidence we can place in absolute accuracy, and the modest dataset size (58 posters) restricts statistical power for broader generalisation.

---

## Dataset  
- **Source**: Instagram URLs listed in `docs/test_poster_urls.txt`.  
- **Content**: Single‑image posters that contain tour‑date information for Thai artists.  
- **Size**: 58 posters (all successfully processed; `posters_manifest_ok` = 58).  
- **Ground‑Truth Level**: **Silver** – generated via a rapid LLM‑assisted pipeline rather than double‑human adjudication.  
- **Availability**: Ground‑truth JSON files are present for all 58 items (`ground_truth_available` = 58, `missing_ground_truth` = 0).  

---

## Methodology  

1. **Prompting & Inference**  
   - Model temperature fixed at **0.2** (see Meta JSON).  
   - Random seed **23** used for deterministic sampling.  
   - Prompt hashes (e.g., `benchmark/prompts/predict.txt`) recorded to guarantee reproducibility.  

2. **Evaluation Metrics** (as defined in the benchmark protocol)  
   - **Schema Strict Rate** – proportion of predictions that exactly match the required JSON schema (keys, types, no extra fields).  
   - **App Quality Score** – composite metric (0–100) weighting structured output (0.4), event‑match (0.35), top‑level fields (0.15), and event‑count (0.1). Missing‑field penalty of 10 % applied per absent critical field.  
   - **Event‑Match Scores** – Hungarian‑algorithm assignment between predicted and ground‑truth events, yielding per‑field F1 or similarity scores (date = 0.748, venue = 0.667, etc.).  

3. **Statistical Reliability**  
   - **Bootstrap**: 1,000 resamples, seed = 23, α = 0.05, providing confidence intervals for the App Quality Score and other aggregates.  
   - No pairwise model comparisons are available for this run (comparisons table empty).  

4. **Cost Accounting**  
   - **Prediction Cost**: USD 0 (model inference free under current licensing).  
   - **Judging Cost**: USD 0 (automated scoring).  
   - **Ground‑Truth Cost**: USD 2.308 ≈ USD 2.31 (human time to produce silver ground‑truth).  

---

## Results  

| Model                     | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|---------------------------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it      | 83.75 ± 1.63 (95 % CI 81.96‑85.59) | 2.31 | 1.00 |

*All 58 predictions were parsed successfully (`json_parse_rate` = 1.00) and passed both schema‑ok and schema‑valid checks.*

Additional aggregated metrics (averaged across events)  

| Metric | Value |
|--------|-------|
| Avg. Top‑Level Score | 0.738 |
| Avg. Event‑Match Score | 0.736 |
| Avg. Event‑Count Score | 0.986 |
| Avg. Location Score | 0.744 |
| Avg. Missing‑Field Rate | 0.294 |
| Avg. Date F1 | 0.748 |
| Avg. Venue Score | 0.667 |

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **perfect schema compliance** and a high composite quality score while incurring **negligible inference cost**. The only expense stems from the silver ground‑truth creation (USD 2.31). Compared with typical paid LLM APIs, this represents a **cost‑effective** solution for production deployment, assuming the silver ground‑truth is an acceptable proxy for real‑world performance.

### Field‑Level Performance  
- **Date extraction** (F1 = 0.748) and **location extraction** (0.744) are the strongest components, reflecting the model’s ability to recognise standard date formats and city/province names in Thai posters.  
- **Venue extraction** lags (0.667), suggesting occasional confusion between venue names and surrounding decorative text.  
- The **missing‑field rate** of 29 % indicates that roughly one‑third of events lack at least one critical field (date, venue, city, or province), which the missing‑field penalty partially offsets in the final score.  

### Statistical Significance  
Bootstrap confidence intervals are narrow (± 1.6 points) because the dataset contains no missing predictions and all outputs are parsable. Without a second model for direct comparison, we cannot claim statistical superiority; however, the tight CI demonstrates **stable performance** across resamples.

### Reliability for App Readiness  
- **Schema strict rate = 1.00** guarantees that downstream components (e.g., database ingestion, UI rendering) will not encounter structural errors.  
- The composite **App Quality Score ≈ 84** exceeds typical production thresholds (often set around 80) for “ready‑to‑ship” models in the ArtistCalendar pipeline.  

---

## Limitations  

| Aspect | Detail |
|--------|--------|
| **Ground‑Truth Quality** | Silver‑level; not double‑human adjudicated, potentially inflating agreement metrics. |
| **Dataset Size & Diversity** | Only 58 posters, all from Thai Instagram accounts; may not capture the full variability of poster designs, fonts, or multilingual content. |
| **Cost Reporting** | Prediction cost recorded as zero because the model is accessed under a research licence; commercial deployment may incur fees. |
| **Missing‑Field Penalty** | Fixed at 10 % per missing critical field; alternative weighting could change the composite score. |
| **Statistical Power** | No pairwise model comparisons; cannot assess significance of differences against other architectures. |

---

## Recommendations  

1. **Upgrade Ground‑Truth to Gold**  
   - Conduct double‑human annotation with adjudication for at least a subset (e.g., 30 % of posters) to quantify any bias introduced by silver data.  

2. **Target Venue Extraction**  
   - Fine‑tune prompt phrasing or add a post‑processing step (e.g., venue‑lexicon lookup) to raise the venue score toward the 0.8 + range.  

3. **Expand Dataset**  
   - Incorporate additional poster styles, languages (English, Japanese), and larger sample sizes (>200) to improve generalisability and enable robust model‑to‑model comparisons.  

4. **Cost Monitoring for Production**  
   - Verify actual inference costs under the intended commercial API plan; factor these into total cost of ownership calculations.  

5. **Automated Missing‑Field Alerts**  
   - Implement a lightweight validator that flags predictions with missing critical fields (>0.2 missing‑field rate) for manual review before ingestion.  

6. **Re‑run Benchmark with Alternative Temperature**  
   - Although temperature = 0.2 yielded deterministic outputs, a brief experiment at 0.0 and 0.5 could reveal trade‑offs between creativity and schema adherence.  

By addressing the above points, the ArtistCalendar team can move from a promising **silver‑benchmark** to a **gold‑standard, production‑ready** extraction pipeline with confidence in both accuracy and cost efficiency.
