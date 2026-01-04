# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the **gemini‑gemma‑3‑27b‑it** model on the ArtistCalendar poster‑extraction task using a **silver‑quality** ground‑truth dataset of 58 Thai tour‑date posters. The model achieved an **App Quality Score** of **83.42 ± 1.54** (95 % CI [81.66, 85.20]) and an **App Core Score** of **81.72 ± 2.02** (95 % CI [79.70, 83.71]). Schema compliance was perfect (strict‑rate = 1.0) and the total monetary cost of the run was **USD 2.31**, entirely attributable to human ground‑truth creation. The results indicate that the model is ready for production deployment in the ArtistCalendar app, delivering high‑quality structured output at negligible inference cost.

---

## Dataset  
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
- **Size**: 58 single‑poster images containing tour‑date information.  
- **Ground‑truth quality**: **Silver** (human‑verified but not double‑annotated gold standard).  
- **Availability**: Ground‑truth JSON files are present for all 58 items; no missing predictions.  

The dataset follows the **ArtistCalendar** schema (top‑level fields, event objects, core event fields) and has been validated with strict schema checks (schema_ok_rate = 1.0, schema_valid_rate = 1.0, json_parse_rate = 1.0).

---

## Methodology  

1. **Prompting & Generation**  
   - Temperature: **0.2** (fixed for reproducibility).  
   - Random seed: **23** (applied to model sampling and bootstrap).  
   - Prompt hashes are recorded in the meta‑JSON (e.g., `benchmark/prompts/predict.txt` hash = `d01e5c…`).  

2. **Scoring**  
   - **App Quality Score** combines weighted components: structured output (0.4), event‑match (0.35), top‑level fields (0.15), and event‑count (0.1).  
   - **App Core Score** uses the same weighting but restricts event‑match to the core fields (date, venue, city, province, country).  
   - Missing‑field penalty of **10.0** points is applied per absent core field.  

3. **Statistical Reliability**  
   - Bootstrap with **1 000** resamples, seed = 23, α = 0.05.  
   - 95 % confidence intervals are reported for both scores.  

4. **Cost Accounting**  
   - Prediction cost: **USD 0.00** (model inference free in this run).  
   - Human ground‑truth creation cost: **USD 2.308029**.  
   - Total cost: **USD 2.308029**.  

All steps were executed via the `benchmark/benchmark.py publish` command to ensure reproducibility.

---

## Results  

| Model                     | App Quality Score | App Core Score | Total Cost (USD) | Schema Strict Rate |
|---------------------------|-------------------|----------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it      | 83.42 ± 1.54      | 81.72 ± 2.02   | 2.31             | 1.0                |

*Values are mean ± half‑width of the 95 % CI unless otherwise noted.*  

Additional performance indicators (averaged across the 58 posters):  

- **Avg. Top‑Level Score**: 0.744  
- **Avg. Event‑Match Score**: 0.707  
- **Avg. Core‑Event Match Score**: 0.659  
- **Avg. Event‑Count Score**: 0.986  
- **Avg. Missing‑Field Rate**: 0.235 (≈ 23 % of events missing at least one core field)  

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (≥ 80 % on both composite scores) while incurring **no inference cost**. The only expense is the one‑time human effort required to produce the silver ground‑truth, amounting to **USD 2.31** for the entire benchmark. This cost‑to‑accuracy ratio is exceptionally favorable for a production setting where inference volume will be large.

### Schema Reliability  
A **schema strict rate of 1.0** demonstrates that every JSON response adhered exactly to the required keys and types, eliminating downstream parsing errors. The perfect `json_parse_rate` further confirms that the model’s output is ready for direct ingestion by the ArtistCalendar backend.

### Event‑Level Performance  
- The **event‑match score (0.707)** indicates that roughly 71 % of predicted events align with the ground‑truth on weighted fields (date, venue, city, etc.).  
- The **core‑event match (0.659)** is slightly lower, reflecting the impact of the missing‑field penalty (average missing‑field rate = 23 %).  
- The **event‑count score (0.986)** shows that the model almost always predicts the correct number of events per poster, a critical factor for user trust.

### Statistical Significance  
No pairwise model comparisons are available in the supplied data (the “Model comparisons” table is empty). Consequently, we cannot claim statistically significant superiority over alternative models. However, the narrow bootstrap confidence intervals (≈ ± 2 points) suggest that the observed scores are stable across resampling.

---

## Limitations  

- **Ground‑Truth Quality**: The benchmark uses **silver** ground truth. While human‑verified, it lacks the double‑annotation and adjudication required for a gold standard, potentially inflating scores.  
- **Dataset Size & Diversity**: Only 58 posters, all from Thai Instagram accounts, limit generalizability to other languages, regions, or poster designs.  
- **Missing‑Field Penalty**: The average missing‑field rate (23 %) indicates that the model still struggles with extracting some core fields (e.g., venue or city) from certain typographic styles.  
- **Cost Reporting**: Prediction cost is recorded as zero; in a real‑world cloud deployment, inference would incur compute charges not captured here.  

---

## Recommendations  

1. **Proceed to Production**  
   - Deploy **gemini‑gemma‑3‑27b‑it** for the ArtistCalendar app, leveraging its perfect schema compliance and high composite scores.  

2. **Enhance Missing‑Field Extraction**  
   - Fine‑tune prompt engineering or incorporate a post‑processing step (e.g., targeted OCR for venue lines) to reduce the missing‑field rate, which would lift both the App Quality and Core scores.  

3. **Expand Benchmark Dataset**  
   - Augment the dataset with additional languages (English, Japanese) and varied poster layouts to validate cross‑regional robustness.  
   - Create a **gold** ground‑truth subset (double annotation + adjudication) for future high‑stakes releases.  

4. **Monitor Inference Costs**  
   - Track actual cloud inference expenses once the model is served at scale; incorporate these costs into future cost‑benefit analyses.  

5. **Statistical Comparison**  
   - Run parallel evaluations with alternative LLMs (e.g., GPT‑4o, Claude‑3.5) under identical settings to populate the “Model comparisons” table and identify statistically significant differences.  

---

*Reproducibility details*: temperature = 0.2, seed = 23, bootstrap = 1 000 samples (seed = 23, α = 0.05). Prompt hashes and scoring weights are fully recorded in the meta‑JSON, ensuring that any future run can be replicated exactly.  

---  

*Prepared on 2026‑01‑04 (generated_at: 2026‑01‑04T11:05:36+00:00).*
