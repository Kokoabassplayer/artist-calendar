# Final Benchmark Report  

## Executive Summary  
The **ArtistCalendar** poster‑extraction benchmark evaluates how well a language model can convert Thai tour‑date poster images into app‑ready JSON. Using a **silver‑quality** ground‑truth set (human‑verified not required) for 58 posters, the model **gemini‑gemma‑3‑27b‑it** achieved an **App Quality Score** of **83.74 ± 1.64 (95 % CI [81.94, 85.58])** and an **App Core Score** of **82.28 ± 2.01 (95 % CI [80.27, 84.33])**.  

All schema checks passed (strict‑rate = 1.0) and the total monetary cost of the run was **$2.31 USD**, entirely attributable to the creation of silver ground‑truth data (prediction cost = $0). The benchmark was run with a fixed temperature of **0.2** and random seed **23**, and bootstrap confidence intervals were generated from **1 000** resamples (seed = 23, α = 0.05).  

These results indicate that the model can reliably produce structured output suitable for immediate integration into the ArtistCalendar app, while keeping inference cost negligible. However, the reliance on silver ground truth and the modest dataset size limit the statistical power of any broader conclusions.

---

## Dataset  

| Attribute | Value |
|-----------|-------|
| **Source** | Instagram poster URLs listed in `docs/test_poster_urls.txt`. |
| **Number of posters** | 58 (all manifest‑ok). |
| **Language / Region** | Primarily Thai (some English), Thailand‑focused events. |
| **Ground‑truth quality** | **Silver** (LLM‑generated, not human‑verified). |
| **Ground‑truth cost** | $2.308 USD (human annotation not performed). |
| **Inclusion criteria** | Single‑image posters containing tour‑date information. |
| **Exclusion criteria** | Multi‑image carousels, non‑tour announcements, posters lacking dates. |
| **Versioning** | SHA‑256 hash of URL list & manifest recorded in `benchmark/report/meta.json`. |

The dataset is deliberately small to enable rapid iteration. Posters exhibit a wide variety of typographic styles, which introduces OCR difficulty variance.

---

## Methodology  

1. **Prompting & Inference**  
   * Model: `gemini-gemma-3-27b-it`.  
   * Temperature: **0.2** (fixed for reproducibility).  
   * Seed: **23** (applied to any stochastic components).  
   * Prompt hash used for prediction: `d01e5ce0022d1b0f993f11d290c8e8c73d2cc167d5f1035d6e5c4e6eea2ab391`.  

2. **Ground‑Truth Generation**  
   * Silver ground truth was produced via an LLM pipeline (prompt `ground_truth.txt`).  
   * Cost recorded as `$2.308 USD`.  

3. **Scoring**  
   * **Schema strict rate** – exact key and type match (no extra fields).  
   * **App Quality Score** – weighted composite of structured output (0.4), event‑match (0.35), top‑level fields (0.15), and event‑count (0.1).  
   * **App Core Score** – same composite but event‑match limited to core fields (date, venue, city, province, country).  
   * Missing‑field penalty of **10.0** applied per absent core field.  

4. **Statistical Reliability**  
   * Bootstrap with **1 000** resamples, seed = 23, α = 0.05.  
   * Confidence intervals reported for both scores.  

5. **Reproducibility**  
   * All prompt hashes, weights, temperature, and seed values are stored in the provided Meta JSON.  
   * The benchmark can be regenerated with `benchmark/benchmark.py publish` using the same metadata.  

No pairwise model comparisons were available; the “Model comparisons” table is therefore empty.

---

## Results  

| Model | App Quality Score | App Core Score | Total Cost (USD) | Schema Strict Rate |
|-------|-------------------|----------------|------------------|--------------------|
| gemini‑gemma‑3‑27b‑it | **83.74** (95 % CI [81.94, 85.58]) | **82.28** (95 % CI [80.27, 84.33]) | **2.308** | **1.0** |

*All other rates (schema_valid_rate, json_parse_rate, etc.) were also 1.0.*  

Additional per‑metric averages (for reference):  

- Top‑level field match: **0.738**  
- Event match (full): **0.735**  
- Core event match: **0.694**  
- Event count match: **0.986**  
- Location‑related scores (venue 0.667, city 0.742, etc.)  

Missing‑field rate averaged **0.292**, reflecting occasional absent date or venue entries in predictions.

---

## Interpretation  

### Accuracy vs. Cost  
The model delivers **high‑quality structured output** (≥ 82 % on both composite scores) while incurring **zero inference cost**. The only expense stems from generating silver ground truth, which is modest at $2.31 for the entire run. This cost profile is attractive for production where inference budgets are tight.

### Statistical Significance  
Bootstrap confidence intervals are narrow (≈ ± 2 points), indicating stable performance across the 58‑poster sample. However, without a second model for direct comparison, we cannot claim statistical superiority over alternatives. The lack of p‑values or mean‑difference data precludes formal significance testing in this report.

### Schema Reliability  
A **schema strict rate of 1.0** demonstrates that the model consistently emits JSON that conforms exactly to the required schema, eliminating downstream parsing errors. This reliability is crucial for app readiness.

### Trade‑offs  
The **missing‑field penalty** (10 points per absent core field) modestly drags down the scores, reflected in the average missing‑field rate of 0.292. While overall scores remain high, further prompt engineering or post‑processing could reduce these omissions, pushing the app quality above the 90 % threshold often desired for production releases.

---

## Limitations  

1. **Ground‑Truth Quality** – Silver annotations may contain systematic biases; human‑verified (gold) ground truth is absent.  
2. **Dataset Size & Diversity** – Only 58 posters, all from Thai Instagram accounts; results may not generalize to other languages, regions, or poster designs.  
3. **Single‑Model Evaluation** – No comparative models were evaluated; conclusions about relative performance are therefore limited.  
4. **Cost Reporting** – Prediction cost is $0 because the model was run in a free‑tier environment; real‑world deployment may incur compute charges.  
5. **Statistical Power** – With a modest sample, bootstrap CIs are informative but cannot capture rare failure modes.  

---

## Recommendations  

1. **Upgrade Ground Truth** – Produce a **gold** dataset (two independent human annotators + adjudication) for at least a subset (e.g., 30 % of posters) to validate the silver baseline and quantify annotation noise.  
2. **Expand the Corpus** – Increase the poster count to ≥ 200 and incorporate additional languages (e.g., English, Japanese) to test model robustness across typographic variations.  
3. **Model Portfolio** – Run the same benchmark on at least two additional LLMs (e.g., Claude‑3‑Opus, GPT‑4‑Turbo) using identical prompts and seeds to enable statistically meaningful pairwise comparisons.  
4. **Prompt Refinement** – Experiment with a “repair_json” post‑processing step (prompt hash `0a570e716aece4fee3d1080dee3582edf868146a99fb8b720918e912bac8a07e`) to lower the missing‑field rate.  
5. **Cost Modeling** – Simulate inference cost under realistic production settings (e.g., GPU vs. CPU pricing) to confirm that the zero‑cost observation holds at scale.  
6. **Continuous Integration** – Integrate the benchmark into the CI pipeline, automatically generating a new run folder with the same meta‑data for each model update.  

By addressing these points, the ArtistCalendar team can move from a promising proof‑of‑concept to a production‑grade extraction pipeline with quantifiable, reproducible performance guarantees.
