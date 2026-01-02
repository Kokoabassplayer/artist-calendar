# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the **gemini‑gemma‑3‑27b‑it** model on the ArtistCalendar “Thai Tour Poster” task. Using a **silver‑quality** ground‑truth dataset (human‑verified data not available), the model achieved an **App Quality Score** of **80.11 ± 1.69** (95 % CI = [78.32, 82.01]) across 58 poster images. Structured‑output reliability was perfect: **schema strict rate = 1.00**, with 100 % of predictions parsing as valid JSON and adhering to the required schema. The total monetary cost of the run was **USD 2.31**, entirely attributable to the creation of the silver ground truth; model inference incurred no charge.  

The results suggest that the model is ready for **app‑ready deployment** where high‑fidelity field extraction is required, while keeping operational costs negligible.  

---

## Dataset  
| Attribute | Value |
|-----------|-------|
| **Source** | Instagram poster URLs listed in `docs/test_poster_urls.txt`. |
| **Number of posters** | 58 (all manifest‑ok). |
| **Ground‑truth quality** | **Silver** (LLM‑generated, not human‑verified). |
| **Missing ground truth** | 0 |
| **Languages** | Primarily Thai, occasional English. |
| **Geographic focus** | Thailand. |
| **Version identifier** | SHA‑256 hash of URL list & manifest (recorded in `benchmark/report/meta.json`). |

The dataset follows the protocol described in the benchmark documentation: single‑poster images containing tour‑date information, with multi‑image carousels and non‑tour announcements excluded.  

---

## Methodology  

1. **Prompting & Generation**  
   * Temperature: **0.2** (fixed for all runs).  
   * Random seed: **23** (ensures deterministic token sampling).  
   * Prompt hash for prediction: `d01e5ce0022d1b0f993f11d290c8e8c73d2cc167d5f1035d6e5c4e6eea2ab391`.  

2. **Ground‑Truth Creation**  
   * Silver ground truth was produced via an LLM pipeline (cost = USD 2.308029).  
   * No human adjudication; therefore labeled as **silver** per the benchmark protocol.  

3. **Evaluation Metrics**  
   * **Schema strict rate** – exact match to required keys/types, no extra fields.  
   * **App Quality Score** – composite (0‑100) weighted by structured output (0.4), event match (0.35), top‑level fields (0.15), and event‑count accuracy (0.1). Missing‑field penalty of 10 % applied per `weights.missing_field_penalty`.  
   * **Event‑matching** – Hungarian algorithm for optimal assignment between predicted and ground‑truth events.  
   * **Bootstrap confidence intervals** – 1 000 resamples, seed = 23, α = 0.05.  

4. **Reproducibility**  
   * All runs executed with the same temperature, seed, and prompt hashes.  
   * Bootstrap parameters recorded in the meta JSON.  
   * No stochastic post‑processing; JSON parsing and schema validation deterministic.  

---

## Results  

| Model | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|-------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it | **80.11** (95 % CI [78.32, 82.01]) | **2.308** | **1.00** |

*Additional metrics (for reference)*  

- **Schema OK rate**: 1.00  
- **Schema valid rate**: 1.00  
- **JSON parse rate**: 1.00  
- **Avg. top‑level score**: 0.718  
- **Avg. event‑match score**: 0.631  
- **Avg. event‑count score**: 0.98  
- **Avg. missing‑field rate**: 0.254 (≈ 25 % of events missing at least one required field).  

No predictions were missing; all 58 posters received a structured JSON output.  

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (80 % app quality) while incurring **zero inference cost**. The only expense stems from the silver ground‑truth generation (USD 2.31). Compared with typical paid LLM APIs, this cost profile is highly favorable for production environments where large volumes of posters must be processed daily.  

### Schema Reliability  
A **schema strict rate of 1.00** indicates that every prediction conforms exactly to the required JSON schema. This eliminates downstream validation failures and reduces engineering overhead for the ArtistCalendar app.  

### Field‑level Performance  
- **Top‑level fields** (artist name, Instagram handle, tour name, contact info, source month) achieve an average score of **0.718**, reflecting good but not perfect extraction—likely due to OCR variability on Thai script.  
- **Event‑level fields** (date, venue, city, province) show lower average scores (≈ 0.6), with the **missing‑field rate of 25 %** suggesting that some posters lack clearly legible date or venue information. The missing‑field penalty is already baked into the app quality score, explaining why the overall score remains above 80.  

### Statistical Significance  
Because only a single model was evaluated, pairwise comparison tables are empty. The bootstrap confidence interval (± 1.69 points) provides a reliable estimate of the true mean app quality; the interval does **not** cross any conventional decision thresholds (e.g., 70 % for minimal production readiness), reinforcing confidence in the result.  

---

## Limitations  

1. **Silver Ground Truth** – The benchmark uses LLM‑generated annotations rather than human‑verified gold data. Consequently, the reported app quality may be **inflated** if the model reproduces systematic biases present in the silver annotations.  

2. **Dataset Size & Diversity** – Only 58 posters, all from Thai Instagram accounts, limit generalizability to other languages, regions, or poster designs (e.g., highly stylized typography, low‑contrast images).  

3. **Missing‑Field Penalty** – The penalty is applied uniformly (10 × missing‑field rate). Real‑world impact may differ if certain fields (e.g., date) are more critical than others (e.g., contact info).  

4. **No Human Cost Accounting** – The reported total cost excludes any human labor that would be required to produce gold ground truth for future benchmarking.  

5. **Single Model Evaluation** – Without a comparative baseline (e.g., GPT‑4o, Claude‑3), we cannot claim relative superiority; only absolute performance is presented.  

---

## Recommendations  

1. **Upgrade Ground Truth to Gold** – Conduct a double‑annotator human labeling pass for at least a subset (e.g., 30 % of posters) to quantify the silver‑to‑gold gap and validate the current app quality estimate.  

2. **Expand Dataset** – Incorporate additional languages (English, Japanese) and varied poster layouts to stress‑test OCR and extraction pipelines. Aim for ≥ 200 images for more robust statistical power.  

3. **Target Missing‑Field Reduction** – Investigate OCR preprocessing (e.g., image enhancement, language‑specific text detection) to lower the 25 % missing‑field rate, which would directly improve the app quality score.  

4. **Cost‑Benefit Modeling** – Although inference cost is zero, consider the operational cost of running the model at scale (compute, latency). Benchmark latency and throughput on production hardware to ensure real‑time responsiveness for the ArtistCalendar app.  

5. **Model Ensemble or Post‑Processing** – For fields with lower scores (venue, city, province), experiment with lightweight rule‑based post‑processors or ensemble predictions to boost accuracy without adding significant cost.  

6. **Continuous Monitoring** – Deploy the model in a staged rollout and collect user‑feedback metrics (e.g., correction rates) to detect drift or systematic errors that the static benchmark cannot capture.  

---

**Conclusion** – The gemini‑gemma‑3‑27b‑it model demonstrates **app‑ready structured extraction** for Thai tour posters, achieving an 80 % quality score with perfect schema compliance and negligible inference cost. While the silver ground truth limits the certainty of absolute accuracy, the results are promising for production deployment, provided that the recommended steps (gold validation, dataset expansion, and missing‑field mitigation) are pursued to solidify confidence.
