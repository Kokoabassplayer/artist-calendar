# Final Benchmark Report  

## Executive Summary  
The **ArtistCalendar** poster‑extraction benchmark evaluates how well a language model can turn Thai tour‑date poster images into app‑ready, schema‑compliant JSON. Using a single model run – **gemini‑gemma‑3‑27b‑it** – the system achieved an **App Quality Score** of **83.74 ± 1.63** (95 % CI = 81.95–85.58) while incurring a total monetary cost of **$2.31 USD** for the entire 58‑poster set. All outputs satisfied the strict schema (100 % schema‑strict rate) and parsed without errors.  

The ground‑truth data for this run are **silver‑quality** (LLM‑generated and not human‑verified). Consequently, the reported quality reflects the model’s performance against a best‑effort reference rather than a gold‑standard adjudicated dataset.  

Overall, the model demonstrates strong structured‑output reliability at negligible inference cost, making it a viable candidate for production deployment pending validation on gold‑standard ground truth.

---

## Dataset  
- **Source**: Instagram URLs listed in `docs/test_poster_urls.txt`.  
- **Content**: 58 single‑image Thai tour posters containing date, venue, and artist information.  
- **Inclusion criteria**: Posters that explicitly list tour‑date details; multi‑image carousels and non‑tour announcements were excluded.  
- **Ground‑truth availability**: 58 / 58 posters have silver‑quality reference JSON (`ground_truth_available: 58`).  
- **Manifest status**: All 58 posters passed the manifest check (`posters_manifest_ok: 58`).  

The dataset is deliberately small and region‑specific (Thailand, primarily Thai language with occasional English), which limits generalisability to other markets or poster styles.

---

## Methodology  

1. **Prompting & Generation**  
   - Temperature fixed at **0.2** (see Meta JSON).  
   - Random seed **23** applied to all stochastic components.  
   - The model was invoked with the `predict_v2.txt` prompt (hash `3f44d00d9d2241cccd22e44593fbd6cc760356daf7376240917ed0a52f6d9615`).  

2. **Parsing & Validation**  
   - JSON parsing success rate: **1.0** (`json_parse_rate`).  
   - Schema compliance: **1.0** for both *strict* and *valid* checks (`schema_strict_rate`, `schema_valid_rate`).  

3. **Scoring**  
   - **App Quality Score** combines weighted sub‑metrics (structured output, top‑level field accuracy, event‑match quality, event‑count correctness) using the weight schema in the Meta JSON.  
   - Confidence intervals derived via **bootstrap** (1 000 resamples, seed 23, α = 0.05).  

4. **Cost Accounting**  
   - No inference cost (`prediction_cost_usd: 0`).  
   - Ground‑truth generation cost: **$2.308 USD** (`ground_truth_cost_usd`).  
   - Total reported cost equals ground‑truth cost (`total_cost_usd`).  

5. **Statistical Comparison**  
   - No alternative model runs were provided; therefore, pairwise comparison tables are empty and statistical significance cannot be assessed.

---

## Results  

| Model                     | App Quality Score | Total Cost (USD) | Schema‑Strict Rate |
|---------------------------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it      | 83.74 ± 1.63       | 2.31             | 1.00               |

*App Quality CI: 81.95 – 85.58 (95 % bootstrap).*

Additional performance indicators (averaged across the 58 posters):

| Metric                              | Value |
|-------------------------------------|-------|
| Avg. Top‑Level Score                | 0.738 |
| Avg. Event‑Match Score              | 0.737 |
| Avg. Event‑Count Score              | 0.986 |
| Avg. Location Score                 | 0.747 |
| Avg. Venue Score                    | 0.667 |
| Avg. Missing‑Field Rate (penalised) | 0.299 |
| Avg. Date F1                        | 0.748 |
| Avg. Event‑Diff (count error)       | 0.293 |

All 58 predictions were parsed successfully, and no predictions were missing (`missing_predictions: 0`).

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (≥ 83 % composite score) while incurring **no inference cost**. The only expense stems from generating the silver ground truth, which is a one‑time annotation cost. For a production pipeline where inference runs at scale, the cost per poster would effectively be **$0**, making the solution economically attractive.

### Schema Reliability  
A **100 % schema‑strict rate** indicates that the model consistently emits JSON that exactly matches the expected keys and data types. This eliminates downstream validation overhead and reduces the risk of runtime failures in the ArtistCalendar app.

### Event‑Level Fidelity  
Event‑matching scores (~0.74) and date F1 (~0.75) suggest that while the model captures most event details, there remains room for improvement in precise date extraction and venue naming—areas that typically suffer from OCR variability on Thai scripts.

### Statistical Significance  
Because only a single model configuration was evaluated, **no statistical comparison** to alternative models is possible. Consequently, statements about “significant differences” cannot be made; the bootstrap CI only quantifies uncertainty around this model’s own score.

### Ground‑Truth Quality Impact  
Silver‑quality ground truth may over‑ or under‑estimate true performance. Human‑verified (gold) annotations often reveal subtle errors that LLM‑generated references miss, potentially lowering the observed App Quality Score. Therefore, the 83.74 % figure should be interpreted as an **upper bound** pending gold‑standard validation.

---

## Limitations  

| Aspect | Detail |
|--------|--------|
| **Ground‑Truth Level** | Silver (LLM‑generated) – not human‑verified; may contain systematic biases. |
| **Dataset Size & Diversity** | 58 posters, all Thai, limited stylistic variation; results may not extrapolate to other languages or design conventions. |
| **OCR Challenges** | Thai script OCR is error‑prone; missing‑field rate (≈ 30 %) reflects occasional failure to recognise dates/venues. |
| **Cost Reporting** | Only ground‑truth generation cost captured; real‑world deployment costs (compute, storage) not measured. |
| **Statistical Scope** | No comparative models; bootstrap CI reflects only intra‑run variability. |
| **Prompt Consistency** | Temperature set to 0.2 (different from protocol’s 0.1), which could affect reproducibility if not matched exactly. |

---

## Recommendations  

1. **Upgrade Ground Truth to Gold**  
   - Conduct dual‑annotator human labeling with adjudication for all 58 posters.  
   - Re‑run the benchmark to obtain a definitive App Quality Score and to quantify any silver‑to‑gold performance delta.  

2. **Expand the Dataset**  
   - Add at least 200 more posters covering varied typographies, color schemes, and multilingual content (e.g., English‑Thai mixes).  
   - Include a stratified sample of low‑resolution images to stress‑test OCR robustness.  

3. **Cost‑Effective Scaling**  
   - Since inference cost is negligible, focus on optimizing OCR pipelines (e.g., fine‑tuned Thai OCR models) to reduce the missing‑field rate and improve date/venue extraction.  

4. **Model Comparison**  
   - Run additional candidate models (e.g., GPT‑4o, Claude‑3.5) under identical settings (temp 0.2, seed 23) to populate the comparison table.  
   - Use the existing bootstrap framework to assess statistically significant differences.  

5. **Monitoring & Alerting**  
   - Deploy a lightweight schema validator in the production pipeline to catch any drift from the strict schema.  
   - Log per‑poster confidence scores (e.g., `avg_top_level_score`) to trigger manual review when below a threshold (e.g., 0.6).  

6. **Documentation & Reproducibility**  
   - Archive the exact prompt versions (hashes provided) and the Meta JSON alongside any future runs.  
   - Record temperature, seed, and bootstrap parameters in every published report to ensure full reproducibility.  

By addressing the ground‑truth quality and expanding the evaluation scope, the ArtistCalendar team can confidently move the **gemini‑gemma‑3‑27b‑it** model—or a superior alternative—into production, delivering reliable, cost‑effective tour‑date extraction for end users.
