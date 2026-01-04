# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the **gemini‑gemma‑3‑27b‑it** model on the ArtistCalendar “Thai Tour Poster” extraction task. Using a **silver‑quality** human‑augmented ground‑truth set of 58 Instagram poster images, the model achieved an **App Quality Score** of **83.54 ± 1.64** (95 % CI [81.77, 85.41]) and an **App Core Score** of **82.05 ± 1.53** (95 % CI [80.08, 84.14]). All predictions conformed strictly to the required JSON schema (schema‑strict rate = 1.0) and incurred a total monetary cost of **$2.31 USD** (ground‑truth annotation cost only; inference was free).  

The results indicate that the model is **app‑ready** for structured poster extraction, delivering high‑fidelity output at negligible inference cost. However, the evaluation is limited to a single model and a silver‑quality reference, so further validation with gold‑standard data and additional models is recommended before production deployment.

---

## Dataset  
- **Source**: Instagram URLs listed in `docs/test_poster_urls.txt`.  
- **Content**: 58 single‑image posters that contain Thai tour‑date information.  
- **Ground‑Truth Quality**: **Silver** (human‑augmented; not fully double‑annotated gold standard).  
- **Availability**: All 58 ground‑truth JSON files are present; no missing entries.  

The dataset is deliberately small to enable rapid iteration. Posters vary widely in typography, layout, and language mix (Thai + English), which creates realistic OCR challenges.

---

## Methodology  

| Aspect | Detail |
|--------|--------|
| **Prompting** | Fixed prompt `benchmark/prompts/predict_v2.txt` (hash `05ed073c2e77ee5f005d8b5d43b0d9f1a6ee6e43616e5d53ae3d7fbe5d2136`). |
| **Model Settings** | Temperature = 0.2, seed = 23 (applied uniformly). |
| **Evaluation Metrics** | • **Schema strict rate** – exact key/type match.<br>• **App Quality Score** – weighted composite (structured 0.4, event‑match 0.35, top‑level 0.15, event‑count 0.1).<br>• **App Core Score** – same composite but event‑match limited to core fields (date, venue, city, province, country).<br>• **Event‑match** – Hungarian optimal assignment; missing‑field penalty = 10.0. |
| **Statistical Reliability** | Bootstrap with 1 000 resamples, seed = 23, α = 0.05. 95 % confidence intervals reported for all scores. |
| **Cost Accounting** | Inference cost = $0 (free API tier).  Ground‑truth annotation cost = $2.308 USD (recorded in `ground_truth_cost_usd`). |
| **Reproducibility** | All runs logged with temperature, seed, bootstrap parameters, and prompt hashes in `meta.json`.  The same configuration can be re‑executed via `benchmark/benchmark.py publish`. |

Only 29 of the 58 predictions were manually judged (the remaining 29 were automatically accepted because schema checks passed and no missing fields were detected). No predictions were missing.

---

## Results  

| Model | App Quality Score | App Core Score | Total Cost (USD) | Schema‑Strict Rate |
|-------|-------------------|----------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it | **83.54** (CI [81.77, 85.41]) | **82.05** (CI [80.08, 84.14]) | **2.308** | **1.0** |

*Additional aggregated metrics* (averaged over judged items):  

- **Avg Top‑Level Score**: 0.735  
- **Avg Event‑Match Score**: 0.725  
- **Avg Core‑Event Match Score**: 0.683  
- **Avg Event‑Count Score**: 0.985  
- **Avg Location Score**: 0.726  
- **Avg Venue Score**: 0.681  
- **Avg Missing‑Field Rate**: 0.273 (≈ 27 % of events lacked at least one required field, penalized by the missing‑field weight).  

All schema‑related rates (valid, ok, strict) were perfect (1.0), and JSON parsing succeeded for every prediction.

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (≈ 83 % of the maximum possible score) while incurring **no inference cost**. The only expense is the human effort required to produce the silver ground‑truth, amounting to $2.31 USD for the entire set. This cost‑to‑accuracy ratio is favorable for production environments where inference budgets are tight.

### Statistical Significance  
Bootstrap confidence intervals are narrow (≈ ± 1.5 points), indicating **stable performance** across resamples. Because only a single model was evaluated, pairwise statistical tests are not applicable; the “Comparisons table” remains empty. Future runs should include multiple models to enable significance testing (e.g., mean‑difference, p‑value) as outlined in the benchmark protocol.

### Structured‑Output Reliability  
A **schema‑strict rate of 1.0** demonstrates that the model consistently emits JSON that passes strict validation, a prerequisite for downstream ingestion by the ArtistCalendar app. The modest missing‑field rate (27 %) suggests that while the model captures most required fields, occasional omissions (often time or ticket info) still occur. The missing‑field penalty is reflected in the slight gap between the perfect event‑count score (0.985) and the overall quality scores.

---

## Limitations  

1. **Ground‑Truth Quality** – The evaluation uses **silver** ground truth; it was not double‑annotated and adjudicated, so some reference errors may exist.  
2. **Single Model** – Only gemini‑gemma‑3‑27b‑it was assessed; conclusions about relative model performance cannot be drawn.  
3. **Dataset Size & Diversity** – 58 posters provide a useful pilot but may not capture the full spectrum of poster designs, fonts, or lighting conditions encountered in the wild.  
4. **Partial Judging** – Only 29 predictions were manually reviewed; the remaining predictions were accepted based on schema compliance, which may overlook subtle content errors.  
5. **Cost Reporting** – Inference cost is $0 only because the model was accessed via a free tier; paid usage could alter the cost profile.  

These constraints should be addressed before declaring the model production‑ready for all use cases.

---

## Recommendations  

1. **Upgrade to Gold Ground Truth** – Conduct a full double‑annotation workflow with adjudication for at least a subset (e.g., 30 % of the dataset) to obtain gold‑standard references.  
2. **Expand Model Set** – Run the same benchmark on additional LLMs (e.g., Claude‑3, GPT‑4o) to populate the comparisons table and identify statistically significant differences.  
3. **Increase Dataset Volume** – Augment the poster collection to 200 + items, ensuring representation of varied layouts, languages, and image qualities.  
4. **Target Missing Fields** – Fine‑tune prompt engineering or post‑processing rules to reduce the missing‑field rate, especially for time and ticket information.  
5. **Cost Monitoring** – If moving to a paid API tier, record inference latency and per‑token cost to evaluate total cost of ownership.  

Implementing these steps will solidify confidence in the model’s **app readiness**, improve the robustness of the benchmark, and provide clearer guidance for production deployment.  

---  

*Report generated on 2026‑01‑04 at 08:33 UTC. All reproducibility parameters (temperature = 0.2, seed = 23, bootstrap = 1 000 samples) are recorded in the accompanying `meta.json`.*
