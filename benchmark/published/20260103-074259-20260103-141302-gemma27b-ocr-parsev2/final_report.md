# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the ability of **gemini‑gemma‑3‑27b‑it** to extract structured tour‑event data from Thai concert‑poster images for the **ArtistCalendar** application. Using a **silver‑quality** ground‑truth dataset (human‑verified data not available), the model achieved an **App Quality Score** of **83.15 ± 1.41** (95 % CI = 81.51–84.92) while incurring a total monetary cost of **$2.31 USD** for ground‑truth generation. All schema‑related checks (strictness, validity, JSON parsing) were perfect (1.0). The results suggest that the model delivers app‑ready output with high fidelity at negligible inference cost, making it a strong candidate for production deployment pending further validation on a gold‑standard dataset.

---

## Dataset  
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
- **Size**: 58 single‑poster images containing tour‑date information.  
- **Ground‑Truth Quality**: **Silver** (generated via LLM‑assisted annotation; human‑verified gold data not available).  
- **Manifest**: All 58 posters have corresponding ground‑truth entries (`posters_manifest_ok = 58`, `ground_truth_available = 58`).  
- **Missing Data**: None (`missing_ground_truth = 0`).  

The dataset reflects Thai‑language concert posters with varied typography and layout, which introduces OCR challenges but is representative of the target user base for ArtistCalendar.

---

## Methodology  

1. **Prompting & Inference**  
   - Model temperature fixed at **0.2** (see Meta JSON).  
   - Random seed **23** used for reproducibility across all stages (prediction, bootstrap).  
   - Prompt hashes are recorded for each stage (e.g., `benchmark/prompts/predict.txt` hash `d01e5c…`).  

2. **Evaluation Metrics** (as defined in the benchmark protocol)  
   - **Schema Strict Rate** – exact match to the required JSON schema (keys, types, no extra fields).  
   - **App Quality Score** – composite 0‑100 metric weighted by structured output, top‑level field accuracy, event‑match quality, and event‑count correctness (weights detailed in `benchmark/report/meta.json`).  
   - **Event‑Match Scores** – Hungarian‑algorithm assignment between predicted and ground‑truth events, yielding sub‑scores for date F1, venue, location, etc.  
   - **Missing‑Field Penalty** – applied per missing critical field (penalty = 10.0).  

3. **Statistical Reliability**  
   - Bootstrap resampling: 1,000 samples, seed = 23, α = 0.05.  
   - 95 % confidence intervals derived from bootstrap distributions.  

4. **Cost Accounting**  
   - Prediction cost: $0 (model inference free for this run).  
   - Ground‑truth generation cost: $2.308 USD (LLM‑assisted annotation).  
   - Total cost per run: **$2.308 USD**.  

No maximum output token caps were recorded in the metadata; therefore, they are **not available**.

---

## Results  

| Model                     | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|---------------------------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it      | 83.15 (95 % CI 81.51‑84.92) | 2.308 | 1.0 |

**Key metric breakdown (averages across 58 posters)**  

| Metric                              | Value |
|-------------------------------------|-------|
| Avg. Top‑Level Score                | 0.734 |
| Avg. Event‑Match Score              | 0.71 |
| Avg. Event‑Count Score              | 0.987 |
| Avg. Location Score                 | 0.658 |
| Avg. Venue Score                    | 0.671 |
| Avg. Missing‑Field Rate             | 0.258 |
| Avg. Event Difference (count)       | 0.207 |
| Avg. Date F1                        | 0.748 |
| JSON Parse Rate                     | 1.0 |
| Schema OK Rate                      | 1.0 |
| Schema Valid Rate                   | 1.0 |
| Schema Strict Rate                  | 1.0 |

All 58 predictions were successfully parsed as valid JSON, and every output conformed exactly to the required schema.

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (83 % app‑quality) while incurring **zero inference cost**. The only monetary expense stems from the silver‑quality ground‑truth creation ($2.31 USD total, ≈ $0.04 per poster). This cost profile is highly favorable for scaling the extraction pipeline in production, where inference can be run at massive volume without additional expense.

### Trade‑offs in Field Accuracy  
- **Event‑Count Score (0.987)** indicates that the model almost always predicts the correct number of events per poster.  
- **Date F1 (0.748)** and **Location/Venue scores (≈ 0.66‑0.67)** are lower, reflecting the inherent difficulty of OCR on Thai scripts and varied poster layouts.  
- The **Missing‑Field Rate (0.258)** shows that roughly one‑quarter of predictions omit at least one critical field, which the missing‑field penalty partially mitigates in the composite score.  

Despite these gaps, the strict schema adherence ensures that downstream components (e.g., database ingestion, UI rendering) receive well‑formed JSON, reducing the need for error handling.

### Statistical Significance  
Only a single model was evaluated; therefore, pairwise statistical comparisons are **not applicable** (the “Model comparisons” table remains empty). The bootstrap confidence interval around the App Quality Score (± 1.41 points) provides a reliable estimate of performance variability across the 58‑poster sample.

---

## Limitations  

1. **Ground‑Truth Quality** – The benchmark uses **silver** ground truth generated by an LLM rather than human‑verified gold annotations. Consequently, the reported App Quality Score may be inflated or deflated relative to a true gold standard.  
2. **Dataset Size & Diversity** – With only 58 posters, statistical power is limited, and the sample may not capture the full spectrum of poster designs, fonts, or lighting conditions encountered in the wild.  
3. **Language & Regional Bias** – All posters are Thai‑language and Thailand‑centric; results may not generalize to other languages or regions without further testing.  
4. **Missing Output Caps** – No information on maximum token or character limits was provided; extreme‑length outputs could affect downstream processing.  
5. **Cost Scope** – Only annotation cost is accounted for; real‑world deployment may incur additional expenses (e.g., OCR services, storage, monitoring).  

---

## Recommendations  

1. **Proceed to Gold‑Standard Validation** – Conduct a human‑annotated (gold) run on the same 58 posters to quantify the gap between silver and gold performance.  
2. **Targeted Fine‑Tuning** – Investigate modest fine‑tuning or prompt engineering focused on date and venue extraction to reduce the missing‑field rate and improve Date F1.  
3. **Expand the Dataset** – Augment the benchmark with at least 200 additional posters covering varied styles, languages (e.g., English, Japanese), and formats to improve robustness and statistical confidence.  
4. **Implement Post‑Processing Checks** – Although schema strictness is perfect, a lightweight validation layer that flags missing critical fields (date, venue) can trigger fallback OCR or human review, further raising app‑readiness.  
5. **Monitor Production Costs** – Track inference latency and any hidden cloud‑service fees when scaling to thousands of daily images to ensure the “zero‑cost” claim holds in practice.  

By addressing the silver‑ground‑truth limitation and broadening the evaluation set, the team can confidently certify **gemini‑gemma‑3‑27b‑it** as an app‑ready extraction engine for ArtistCalendar, delivering high‑quality structured data at negligible operational cost.
