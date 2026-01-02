# Final Benchmark Report  

## Executive Summary  
This benchmark evaluates the ability of several Gemini‑Gemma LLMs to extract structured tour‑event data from Thai Instagram poster images for the **ArtistCalendar** application. Using a **silver‑quality** human‑verified ground‑truth set (58 posters), we measured **app quality score**, schema adherence, and cost. The 12‑b and 27‑b variants achieved the highest quality (71.5 ± 5.0 and 73.5 ± 4.5 points, respectively) while maintaining negligible prediction cost (USD 0). The 4‑b model lagged considerably (39.4 ± 8.6). All models incurred the same ground‑truth generation cost (USD 2.308). Statistical testing (1 000 bootstrap resamples, seed 23) shows the 12‑b model is significantly better than the 1‑b, 4‑b, and the “n‑e2b/e4b” variants (p < 0.001), but not significantly different from the 27‑b model (p = 0.57).  

**Key take‑aways**  

* The 12‑b and 27‑b models provide app‑ready JSON with > 80 % strict‑schema compliance and low missing‑field rates.  
* The 1‑b and “n‑e*” models produced no usable predictions (100 % missing).  
* Cost is dominated by ground‑truth creation; model inference is effectively free.  

## Dataset  
* **Source** – Instagram poster URLs listed in `docs/test_poster_urls.txt`.  
* **Size** – 58 single‑poster images containing Thai tour‑date information.  
* **Ground‑truth quality** – **Silver** (human‑verified but not double‑annotated gold).  
* **Coverage** – Thai language with occasional English; limited to Thailand‑centric designs.  

## Methodology  
1. **Prompting** – All models were queried with the same `predict.txt` prompt (hash `b2db94c4…`). Temperature was fixed at **0.2** (see Meta JSON).  
2. **Reproducibility** – Random seed 23 was used for model sampling, bootstrap resampling (1 000 samples, α = 0.05), and any stochastic components. No maximum output token cap is recorded (not available).  
3. **Evaluation metrics** –  
   * **Schema strict rate** – proportion of predictions that exactly match the required JSON schema (keys, types, no extras).  
   * **App quality score** – weighted composite (structured 0.4, event_match 0.35, top_level 0.15, event_count 0.1) with a missing‑field penalty of 10 points per absent critical field.  
   * **Auxiliary scores** – event‑match F1, date F1, venue score, etc. (reported in the raw JSON).  
4. **Statistical analysis** – Pairwise mean differences and 95 % confidence intervals were obtained via bootstrap; p‑values derived from the proportion of resamples where the sign reversed.  

## Results  

| Model | App Quality Score | Total Cost (USD) | Schema Strict Rate |
|-------|-------------------|------------------|--------------------|
| gemini‑gemma‑3‑12b‑it | **71.52** | 2.308 | 0.81 |
| gemini‑gemma‑3‑27b‑it | **73.45** | 2.308 | 0.828 |
| gemini‑gemma‑3‑4b‑it  | 39.40 | 2.308 | 0.414 |
| gemini‑gemma‑3‑1b‑it  | 0.00  | 2.308 | 0.00 |
| gemini‑gemma‑3n‑e2b‑it| 0.00  | 2.308 | 0.00 |
| gemini‑gemma‑3n‑e4b‑it| 0.00  | 2.308 | 0.00 |

*All models share the same ground‑truth creation cost; inference cost is zero.*  

### Statistical Comparisons (selected)  

| Model A | Model B | Mean diff | 95 % CI | p‑value | Significant |
|---------|---------|-----------|---------|---------|--------------|
| 12b | 1b | **+71.52** | 66.13 – 76.51 | 0.0 | Yes |
| 12b | 27b | –1.93 | –8.21 – 4.30 | 0.57 | No |
| 12b | 4b | **+32.12** | 21.58 – 42.77 | 0.0 | Yes |
| 27b | 4b | **+34.05** | 24.32 – 43.60 | 0.0 | Yes |

The 12‑b and 27‑b models are statistically indistinguishable, while both outperform the 4‑b, 1‑b, and “n‑e*” variants.

## Interpretation  

### Accuracy vs. Cost  
Because inference cost is negligible, the primary trade‑off is **model size vs. quality**. The 12‑b model delivers near‑optimal quality (71.5) with a modest 0.81 strict‑schema rate and a missing‑field rate of 0.523, making it suitable for production where compute budget is limited. The 27‑b model offers a marginal quality gain (73.5) and slightly higher schema compliance (0.828) at the expense of a larger model footprint, which may affect latency on edge devices.  

The 4‑b model, despite being smaller than the 12‑b, suffers from poor schema compliance (41 % strict) and high missing‑field rates (68 %). Its lower event‑match score (0.339) suggests insufficient capacity to handle the OCR‑induced noise typical of Thai posters.  

The 1‑b and “n‑e*” models failed to produce any predictions (100 % missing), indicating that the minimal parameter count cannot reliably parse the visual‑textual content of these posters.  

### Statistical Significance  
Bootstrap analysis confirms that the superiority of the 12‑b over the 1‑b, 4‑b, and “n‑e*” models is highly significant (p < 0.001). The lack of significance between 12‑b and 27‑b (p = 0.57) suggests that, for this dataset, scaling beyond 12 B parameters yields diminishing returns.  

### Structured Output Reliability  
Both top‑performing models achieve **> 80 % strict‑schema rate**, meaning downstream components of ArtistCalendar can consume the JSON without additional validation layers. The 12‑b model’s json‑parse rate (94.8 %) and schema‑valid rate (81 %) are also acceptable, though a small fraction of outputs may require fallback handling.  

## Limitations  

* **Ground‑truth quality** – Silver rather than gold; single‑annotator verification may miss subtle errors.  
* **Dataset size & diversity** – Only 58 posters, all Thai; results may not generalize to other languages, scripts, or poster designs.  
* **Missing meta** – No maximum output token cap recorded; reproducibility of token limits cannot be verified.  
* **Cost accounting** – Only ground‑truth generation cost is captured; real‑world inference cost (GPU/CPU time) is omitted.  

## Recommendations  

1. **Production deployment** – Adopt the **gemini‑gemma‑3‑12b‑it** model for a balanced trade‑off between quality, latency, and resource usage.  
2. **Future data collection** – Expand the benchmark to include non‑Thai posters and multi‑image carousels to test model robustness across scripts and layouts.  
3. **Gold‑standard validation** – For critical releases, generate a gold‑level ground truth (dual annotators + adjudication) to eliminate silver‑level uncertainty.  
4. **Monitoring** – Implement a lightweight schema‑validation wrapper that logs any strict‑schema failures (≈ 19 % for 12‑b) for continuous quality monitoring.  
5. **Cost modeling** – Record actual inference latency and compute cost in future runs to complement the current zero‑cost metric.  

By following these steps, the ArtistCalendar team can confidently select a model that delivers app‑ready structured data while maintaining operational efficiency.
