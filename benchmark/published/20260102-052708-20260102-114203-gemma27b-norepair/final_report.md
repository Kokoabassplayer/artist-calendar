# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the **gemini‑gemma‑3‑27b‑it** model on the ArtistCalendar “Thai Tour Poster” extraction task. Using a **silver‑quality** ground‑truth dataset of 58 Instagram poster images, the model achieved an **App Quality Score** of **79.52 ± 1.74 (95 % CI [77.72, 81.46])** while incurring a total monetary cost of **$2.31 USD**. Schema compliance was perfect (strict‑rate = 1.0). The run was fully reproducible (temperature = 0.2, seed = 23, bootstrap = 1 000 samples, α = 0.05).  

The results suggest that the model delivers app‑ready structured JSON at modest cost, but the modest event‑level scores (e.g., venue 0.49, date F1 0.69) indicate room for improvement before production deployment.

---

## Dataset  
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
- **Size**: 58 single‑poster images containing Thai tour‑date information.  
- **Ground‑Truth Quality**: **Silver** (LLM‑generated and subsequently validated, not human‑verified).  
- **Availability**: All ground‑truth files are present (`ground_truth_available = 58`, `missing_ground_truth = 0`).  

The dataset reflects Thai‑language posters with varied typography and layout, which may affect OCR performance.

---

## Methodology  

1. **Prompting & Generation**  
   - Temperature fixed at **0.2** for all model calls.  
   - Random seed **23** used for deterministic sampling.  
   - Prompt hashes are recorded (e.g., `benchmark/prompts/predict.txt` hash `d01e5c…`).  

2. **Evaluation Metrics** (as defined in the benchmark protocol)  
   - **Schema Strict Rate** – exact match to the required JSON schema (keys, types, no extras).  
   - **App Quality Score** – composite weighted score (structured 0.4, event_match 0.35, top_level 0.15, event_count 0.1) with a missing‑field penalty of 10.0.  
   - **Event‑level Scores** – top‑level, event‑match, event‑count, location, venue, date‑F1, etc.  
   - **Bootstrap Confidence Intervals** – 1 000 resamples, seed 23, α = 0.05.  

3. **Cost Accounting**  
   - Prediction cost: $0 (model run free in this evaluation).  
   - Ground‑truth generation cost: **$2.308 USD**.  
   - Total cost per run: **$2.308 USD**.  

4. **Reproducibility**  
   - All hyper‑parameters (temperature, seed, bootstrap settings) are stored in `meta.json`.  
   - The same prompt versions and scoring weights were used throughout.  

---

## Results  

| Model                     | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|---------------------------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it      | 79.52 ± 1.74       | 2.308            | 1.0                |

*App Quality CI95: [77.72, 81.46]; Standard deviation = 7.349.*  

Additional aggregated metrics (averaged across the 58 posters):  

| Metric                     | Value |
|----------------------------|-------|
| Avg Top‑Level Score        | 0.746 |
| Avg Event‑Match Score      | 0.652 |
| Avg Event‑Count Score      | 0.981 |
| Avg Location Score         | 0.669 |
| Avg Venue Score            | 0.491 |
| Avg Missing‑Field Rate    | 0.43  |
| Avg Date F1                | 0.687 |
| Avg Event Diff (pred‑gold)| 0.397 |

No pairwise comparison table is provided because only a single model was evaluated in this run.

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **perfect schema compliance** (1.0 strict rate) at a negligible prediction cost, confirming that the JSON structure is reliably produced. However, the **event‑level components** (venue 0.49, date F1 0.69) pull the overall App Quality Score down to the high‑70s. In a production setting where users rely on accurate venue and date information, these sub‑80 scores may translate into noticeable user friction.

Given the **total cost of $2.31 USD** for the entire dataset, the cost per poster is **≈ $0.04**, which is well within typical SaaS budgets. The cost is dominated by the silver ground‑truth generation; the model inference itself is free in this evaluation.

### Statistical Significance  
Bootstrap confidence intervals indicate that the observed App Quality Score is statistically stable (CI width ≈ 3.7 points). Because no alternative models were benchmarked, we cannot claim a statistically significant advantage over other approaches. Future runs should include at least one baseline (e.g., GPT‑4o) to enable pairwise significance testing.

### Structured‑Output Reliability  
The **schema strict rate of 1.0** and **JSON parse rate of 1.0** demonstrate that the model consistently emits syntactically correct JSON, a prerequisite for downstream ingestion. The **missing‑field penalty** (average rate 0.43) shows that roughly 43 % of the expected fields are omitted or empty, which directly reduces the composite quality score. Targeted prompt engineering or post‑processing could mitigate this.

---

## Limitations  

| Aspect | Detail |
|--------|--------|
| **Ground‑Truth Quality** | Silver (LLM‑generated) – may contain systematic biases; not a gold‑standard human annotation. |
| **Dataset Size & Diversity** | Only 58 Thai posters; limited stylistic variety may not generalize to other regions or languages. |
| **Missing Field Penalty** | High average missing‑field rate (0.43) suggests the evaluation may penalize the model for fields that are optional in real‑world usage. |
| **Cost Reporting** | Prediction cost recorded as $0; actual compute cost on cloud infrastructure is not captured. |
| **Single‑Model Evaluation** | No comparative baseline; statistical significance of differences cannot be assessed. |

---

## Recommendations  

1. **Upgrade Ground‑Truth to Gold**  
   - Conduct dual human annotation with adjudication to obtain gold‑standard labels. This will provide a more reliable ceiling for model performance.  

2. **Expand the Dataset**  
   - Increase the number of posters (≥ 200) and incorporate varied languages and design styles to improve external validity.  

3. **Prompt & Post‑Processing Enhancements**  
   - Experiment with higher temperature (e.g., 0.4) or few‑shot examples to reduce the missing‑field rate.  
   - Implement a lightweight validation‑repair step (e.g., `repair_json.txt` prompt) before final scoring.  

4. **Benchmark Additional Models**  
   - Run at least one strong baseline (e.g., GPT‑4o) and one smaller, cheaper model to populate the comparison table and enable statistical pairwise testing.  

5. **Cost Transparency**  
   - Record actual compute time and associated cloud charges for inference to provide a complete cost‑benefit picture.  

6. **Monitoring in Production**  
   - Deploy a small‑scale A/B test of the current model in the ArtistCalendar app, tracking user‑reported errors (incorrect dates/venues) to validate that the App Quality Score correlates with real‑world satisfaction.  

By addressing the silver‑ground‑truth limitation and broadening the evaluation scope, future benchmark runs will yield more actionable insights for selecting a model that balances **high extraction accuracy**, **schema reliability**, and **operational cost** for the ArtistCalendar application.
